
"""Blockchain Lab 03 - Ledger and transaction state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


MAX_TARGET = (1 << 256) - 1
GENESIS_TARGET = MAX_TARGET >> 16


def sha256d(data: bytes) -> bytes:
    """Calculate double SHA-256."""
    first = hashlib.sha256(data).digest()
    return hashlib.sha256(first).digest()


@dataclass(frozen=True)
class Transaction:
    sender: str
    recipient: str
    amount: int
    nonce: int
    fee: int = 0

    @property
    def txid(self) -> str:
        data = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "nonce": self.nonce,
            "fee": self.fee,
        }
        encoded = json.dumps(data, sort_keys=True).encode()
        return sha256d(encoded).hex()


class State:
    """Track account balances and transaction nonces."""

    def __init__(self, balances=None):
        self.balances = dict(balances or {})
        self.nonces = {}

    def balance_of(self, account: str) -> int:
        return self.balances.get(account, 0)

    def nonce_of(self, account: str) -> int:
        return self.nonces.get(account, 0)

    def copy(self):
        new_state = State(self.balances)
        new_state.nonces = self.nonces.copy()
        return new_state

    def validate(self, tx: Transaction):
        """Return an error message or None if valid."""

        if tx.amount < 0 or tx.fee < 0:
            return "negative amount"

        if self.balance_of(tx.sender) < tx.amount + tx.fee:
            return "insufficient balance"

        expected_nonce = self.nonce_of(tx.sender)

        if tx.nonce != expected_nonce:
            return (
                f"nonce mismatch: expected {expected_nonce}, "
                f"got {tx.nonce}"
            )

        return None

    def apply(self, tx: Transaction):
        """Apply a transaction to the current state."""

        error = self.validate(tx)

        if error is not None:
            raise ValueError(error)

        self.balances[tx.sender] = (
            self.balance_of(tx.sender) - tx.amount - tx.fee
        )

        self.balances[tx.recipient] = (
            self.balance_of(tx.recipient) + tx.amount
        )

        self.nonces[tx.sender] = tx.nonce + 1





import time
from dataclasses import replace


@dataclass(frozen=True)
class Block:
    height: int
    prev_hash: str
    timestamp: float
    txs: tuple[Transaction, ...] = ()
    difficulty: int = 1
    nonce: int = 0
    miner: str = ""

    @property
    def target(self) -> int:
        return GENESIS_TARGET // max(1, self.difficulty)

    @property
    def merkle_root(self) -> str:
        if not self.txs:
            return "00" * 32

        txids = "".join(tx.txid for tx in self.txs)
        return sha256d(txids.encode()).hex()

    def header_bytes(self, nonce=None) -> bytes:
        data = {
            "height": self.height,
            "prev": self.prev_hash,
            "ts": round(self.timestamp, 6),
            "root": self.merkle_root,
            "diff": self.difficulty,
            "miner": self.miner,
            "nonce": self.nonce if nonce is None else nonce,
        }
        return json.dumps(data, sort_keys=True).encode()

    @property
    def hash(self) -> str:
        return sha256d(self.header_bytes()).hex()

    @property
    def work(self) -> int:
        return MAX_TARGET // max(1, self.target)

    def is_valid_pow(self) -> bool:
        return int(self.hash, 16) < self.target

    def with_nonce(self, nonce: int):
        return replace(self, nonce=nonce)


def genesis_block(difficulty: int = 1) -> Block:
    return Block(
        height=0,
        prev_hash="00" * 32,
        timestamp=0.0,
        difficulty=difficulty,
    )



@dataclass
class ChainEntry:
    block: Block
    total_work: int


class Chain:
    """Store blocks and select the branch with most accumulated work."""

    def __init__(self, genesis=None):
        genesis = genesis or genesis_block()

        self.entries = {
            genesis.hash: ChainEntry(genesis, genesis.work)
        }

        self.genesis_hash = genesis.hash
        self.tip_hash = genesis.hash
        self.reorg_count = 0
        self.reorg_depths = []

    @property
    def tip(self) -> Block:
        return self.entries[self.tip_hash].block

    @property
    def height(self) -> int:
        return self.tip.height

    @property
    def total_work(self) -> int:
        return self.entries[self.tip_hash].total_work

    def has(self, block_hash: str) -> bool:
        return block_hash in self.entries

    def canonical(self) -> list[Block]:
        blocks = []
        current = self.tip_hash

        while True:
            block = self.entries[current].block
            blocks.append(block)

            if current == self.genesis_hash:
                break

            current = block.prev_hash

        return list(reversed(blocks))

    def path_to(self, block_hash: str) -> list[Block]:
        if block_hash not in self.entries:
            raise KeyError("unknown block")

        blocks = []
        current = block_hash

        while True:
            block = self.entries[current].block
            blocks.append(block)

            if current == self.genesis_hash:
                break

            current = block.prev_hash

        return list(reversed(blocks))

    def add_block(self, block: Block, *, check_pow=True) -> bool:
        """Return True when the canonical tip changes."""

        if self.has(block.hash):
            return False

        parent = self.entries.get(block.prev_hash)

        if parent is None:
            raise KeyError("unknown parent")

        if block.height != parent.block.height + 1:
            raise ValueError("incorrect block height")

        if check_pow and not block.is_valid_pow():
            raise ValueError("invalid proof of work")

        total_work = parent.total_work + block.work

        old_path = self.canonical()
        old_tip = self.tip_hash

        # Keep competing blocks, even when they do not win.
        self.entries[block.hash] = ChainEntry(block, total_work)

        if total_work <= self.total_work:
            return False

        new_path = self.path_to(block.hash)

        old_hashes = {b.hash for b in old_path}
        common_height = 0

        for previous in reversed(new_path):
            if previous.hash in old_hashes:
                common_height = previous.height
                break

        if block.prev_hash != old_tip:
            depth = self.height - common_height

            if depth > 0:
                self.reorg_count += 1
                self.reorg_depths.append(depth)

        self.tip_hash = block.hash
        return True

    def replay_state(self, initial: dict[str, int], reward=50):
        state = State(initial)

        for block in self.canonical()[1:]:
            for tx in block.txs:
                state.apply(tx)

            if block.miner:
                fees = sum(tx.fee for tx in block.txs)
                state.balances[block.miner] = (
                    state.balance_of(block.miner) + reward + fees
                )

        return state

    def block_intervals(self) -> list[float]:
        blocks = self.canonical()
        return [
            blocks[i].timestamp - blocks[i - 1].timestamp
            for i in range(1, len(blocks))
        ]


def make_block(
    chain: Chain,
    *,
    txs: tuple[Transaction, ...] = (),
    difficulty: int | None = None,
    miner: str = "",
    timestamp: float | None = None,
) -> Block:
    return Block(
        height=chain.height + 1,
        prev_hash=chain.tip_hash,
        timestamp=time.time() if timestamp is None else timestamp,
        txs=txs,
        difficulty=chain.tip.difficulty if difficulty is None else difficulty,
        miner=miner,
    )
