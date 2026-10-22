
"""Proof of Work mining for Blockchain Lab 03."""

from __future__ import annotations

from .chain import (
    GENESIS_TARGET,
    Block,
    sha256d,
)


MAX_ADJUSTMENT_FACTOR = 4


def target_from_difficulty(difficulty: int) -> int:
    """Higher difficulty means a smaller target."""
    if difficulty < 1:
        raise ValueError("difficulty must be positive")

    return GENESIS_TARGET // difficulty


def difficulty_from_target(target: int) -> int:
    if target <= 0:
        raise ValueError("target must be positive")

    return max(1, GENESIS_TARGET // target)


def retarget(
    current_difficulty: int,
    actual_seconds: float,
    target_seconds: float,
    *,
    clamp: int = MAX_ADJUSTMENT_FACTOR,
) -> int:
    """Adjust difficulty based on mining time."""

    if current_difficulty < 1:
        raise ValueError("invalid difficulty")

    if target_seconds <= 0 or clamp < 1:
        raise ValueError("invalid retarget parameters")

    if actual_seconds <= 0:
        actual_seconds = target_seconds / clamp

    ratio = actual_seconds / target_seconds

    # Do not allow difficulty to change by more
    # than a factor of four in either direction.
    ratio = max(1 / clamp, min(clamp, ratio))

    return max(1, int(current_difficulty / ratio))


def mine_range(
    block: Block,
    start: int,
    stop: int,
    step: int = 1,
) -> int | None:
    """Search for a valid nonce."""

    if step <= 0:
        raise ValueError("step must be positive")

    for nonce in range(start, stop, step):
        digest = sha256d(block.header_bytes(nonce))
        hash_number = int.from_bytes(digest, "big")

        if hash_number < block.target:
            return nonce

    return None


def mine(block: Block, max_nonce: int = 2**32) -> Block:
    """Mine one block using a single process."""

    nonce = mine_range(block, 0, max_nonce)

    if nonce is None:
        raise RuntimeError("nonce space exhausted")

    return block.with_nonce(nonce)




import multiprocessing as mp
import queue


def _mining_worker(
    block: Block,
    worker_id: int,
    worker_count: int,
    found,
    results,
):
    """Search every worker_count-th nonce."""

    nonce = worker_id

    while nonce < 2**32:

        # Stop when another worker has found a solution.
        if found.is_set():
            return

        # Check nonces in batches to reduce overhead.
        for _ in range(4096):
            if nonce >= 2**32:
                return

            digest = sha256d(block.header_bytes(nonce))
            hash_value = int.from_bytes(digest, "big")

            if hash_value < block.target:
                if not found.is_set():
                    results.put(nonce)
                    found.set()
                return

            nonce += worker_count


def mine_parallel(
    block: Block,
    workers: int = 4,
    timeout: float = 60.0,
) -> Block:
    """Mine a block using multiple Python processes."""

    if workers < 1:
        raise ValueError("workers must be positive")

    if workers == 1:
        return mine(block)

    ctx = mp.get_context("spawn")

    found = ctx.Event()
    results = ctx.Queue()

    processes = [
        ctx.Process(
            target=_mining_worker,
            args=(block, i, workers, found, results),
        )
        for i in range(workers)
    ]

    for process in processes:
        process.start()

    try:
        winning_nonce = results.get(timeout=timeout)

    except queue.Empty:
        raise RuntimeError("parallel mining timed out")

    finally:
        found.set()

        for process in processes:
            process.join(timeout=2)

            if process.is_alive():
                process.terminate()
                process.join()

        results.close()
        results.join_thread()

    mined_block = block.with_nonce(winning_nonce)

    if not mined_block.is_valid_pow():
        raise RuntimeError("invalid mining result")

    return mined_block




import statistics
import time
from dataclasses import dataclass

from .chain import Chain, make_block


@dataclass
class MiningStats:
    intervals: list[float]
    difficulties: list[int]
    hashes_estimated: list[int]

    @property
    def mean_interval(self):
        return statistics.fmean(self.intervals)

    @property
    def median_interval(self):
        return statistics.median(self.intervals)

    @property
    def stdev_interval(self):
        return statistics.pstdev(self.intervals)

    def report(self, target_seconds):
        mean = self.mean_interval
        median = self.median_interval
        stdev = self.stdev_interval

        return (
            f"Blocks mined: {len(self.intervals)}\n"
            f"Target interval: {target_seconds:.3f} s\n"
            f"Mean interval: {mean:.4f} s\n"
            f"Median interval: {median:.4f} s\n"
            f"Standard deviation: {stdev:.4f} s\n"
            f"Median / mean: {median / mean:.3f}\n"
            f"Stdev / mean: {stdev / mean:.3f}"
        )


def simulate_mining(
    blocks=100,
    *,
    retarget_interval=10,
    target_seconds=1.0,
    initial_difficulty=1,
    workers=1,
    miner="miner-0",
):
    """Mine blocks and collect time and difficulty statistics."""

    chain = Chain()
    intervals = []
    difficulties = [initial_difficulty]
    hashes_estimated = []

    difficulty = initial_difficulty
    window_start = time.perf_counter()

    for i in range(blocks):
        started = time.perf_counter()

        candidate = make_block(
            chain,
            difficulty=difficulty,
            miner=miner,
            timestamp=started,
        )

        if workers == 1:
            mined = mine(candidate)
        else:
            mined = mine_parallel(candidate, workers=workers)

        elapsed = time.perf_counter() - started

        chain.add_block(mined)

        intervals.append(elapsed)
        difficulties.append(difficulty)
        hashes_estimated.append(
            (1 << 256) // mined.target
        )

        if (i + 1) % retarget_interval == 0:
            window_elapsed = time.perf_counter() - window_start

            difficulty = retarget(
                difficulty,
                window_elapsed,
                target_seconds * retarget_interval,
            )

            window_start = time.perf_counter()

    return chain, MiningStats(
        intervals,
        difficulties,
        hashes_estimated,
    )
