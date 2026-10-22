
"""Bonus E2: reusable process-based PoW miner."""

import hashlib
import multiprocessing as mp
import time
import queue


def valid_nonce(header, nonce, target):
    data = header + nonce.to_bytes(8, "big")
    digest = hashlib.sha256(data).digest()
    return int.from_bytes(digest, "big") < target



def worker(worker_id, worker_count, tasks, results, stop):
    """Persistent worker with coordinated job completion."""

    while True:
        job = tasks.get()

        if job is None:
            break

        job_id, header, target = job

        nonce = worker_id
        attempts = 0
        found = None

        while nonce < 2**64:
            if attempts % 256 == 0 and stop.is_set():
                break

            attempts += 1

            if valid_nonce(header, nonce, target):
                found = nonce
                stop.set()
                break

            nonce += worker_count

        results.put(
            (job_id, worker_id, found, attempts)
        )
        
        while not stop.is_set() and nonce < 2**64:
            attempts += 1

            if valid_nonce(header, nonce, target):
                found = nonce
                stop.set()
                break

            nonce += worker_count



class PersistentMiner:
    """Reuse a fixed set of workers across mining jobs."""

    def __init__(self, workers=4):
        if workers < 1:
            raise ValueError("workers must be positive")

        self.workers = workers
        self.ctx = mp.get_context("spawn")

        self.tasks = [
            self.ctx.Queue()
            for _ in range(workers)
        ]

        self.results = self.ctx.Queue()
        self.stop_event = self.ctx.Event()

        self.processes = []
        self.job_id = 0

    def __enter__(self):
        for worker_id in range(self.workers):
            process = self.ctx.Process(
                target=worker,
                args=(
                    worker_id,
                    self.workers,
                    self.tasks[worker_id],
                    self.results,
                    self.stop_event,
                ),
            )
            process.start()
            self.processes.append(process)

        return self

    def mine(self, header, target):
        """Mine a block without restarting workers."""

        self.job_id += 1
        job_id = self.job_id
        self.stop_event.clear()

        start = time.perf_counter()

        for queue in self.tasks:
            queue.put((job_id, header, target))

        winning_nonce = None
        attempts = 0

        # Wait for every worker to finish this job.
        # This prevents stale results in the next job.
        
        for _ in range(self.workers):
            while True:
                try:
                    result = self.results.get(timeout=1)
                    break
                except queue.Empty:
                    if any(
                        p.exitcode is not None
                        for p in self.processes
                    ):
                        raise RuntimeError(
                            "A mining worker exited unexpectedly"
                        )

            result_job, worker_id, nonce, count = result


            if result_job != job_id:
                raise RuntimeError("Unexpected job result")

            attempts += count

            if nonce is not None:
                winning_nonce = nonce

        elapsed = time.perf_counter() - start

        if winning_nonce is None:
            raise RuntimeError("No valid nonce found")

        assert valid_nonce(header, winning_nonce, target)

        return {
            "nonce": winning_nonce,
            "elapsed": elapsed,
            "attempts": attempts,
        }


    def worker_status(self):
        """Return worker process information."""
        return [
            {
                "pid": process.pid,
                "alive": process.is_alive(),
                "exitcode": process.exitcode,
            }
            for process in self.processes
        ]


    def __exit__(self, exc_type, exc_value, traceback):
        for queue in self.tasks:
            queue.put(None)

        for process in self.processes:
            process.join(timeout=5)

            if process.is_alive():
                process.terminate()
                process.join()

        for queue in self.tasks:
            queue.close()

        self.results.close()


def main():
    target = (1 << 256) // 10_000

    print("BONUS E2 - PERSISTENT PARALLEL MINER")
    print("=" * 48)

    with PersistentMiner(workers=4) as miner:
        for block_number in range(1, 6):
            header = f"block-{block_number}".encode()

            result = miner.mine(header, target)

            print(
                f"Block {block_number}: "
                f"nonce={result['nonce']}, "
                f"time={result['elapsed']:.4f}s, "
                f"attempts={result['attempts']}"
            )

    print("\nAll 5 blocks mined successfully.")
    print("Worker processes were reused.")


if __name__ == "__main__":
    mp.freeze_support()
    main()
