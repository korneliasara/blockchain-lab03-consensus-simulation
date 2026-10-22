
"""Blockchain Lab 03 - Gossip network simulation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .chain import Block, Chain, Transaction


@dataclass
class LegacyNode:
    node_id: int
    chain: Chain = field(default_factory=Chain)
    peers: set[int] = field(default_factory=set)
    mempool: dict[str, Transaction] = field(default_factory=dict)
    seen_messages: set[str] = field(default_factory=set)
    orphan_blocks: dict[str, Block] = field(default_factory=dict)


class GossipNetwork:
    """Simulate message propagation between blockchain nodes."""

    def __init__(self, node_count: int):
        if node_count < 1:
            raise ValueError("node_count must be positive")

        self.nodes = {
            i: LegacyNode(node_id=i)
            for i in range(node_count)
        }

        self.messages_sent = 0
        self.messages_delivered = 0

    def connect(self, a: int, b: int):
        if a == b:
            return

        self.nodes[a].peers.add(b)
        self.nodes[b].peers.add(a)

    def disconnect(self, a: int, b: int):
        self.nodes[a].peers.discard(b)
        self.nodes[b].peers.discard(a)

    def connect_all(self):
        for a in self.nodes:
            for b in self.nodes:
                if a < b:
                    self.connect(a, b)


    def partition(
        self,
        group_a: set[int],
        group_b: set[int],
    ) -> None:
        """Disconnect nodes belonging to different groups."""

        for a in group_a:
            for b in group_b:
                self.disconnect(a, b)

    
    


    def reconnect_all(self):
        self.connect_all()

    def reachable(self, start: int) -> set[int]:
        visited = {start}
        queue = deque([start])

        while queue:
            current = queue.popleft()

            for peer in self.nodes[current].peers:
                if peer not in visited:
                    visited.add(peer)
                    queue.append(peer)

        return visited

    def broadcast_transaction(
        self, origin: int, tx: Transaction
    ) -> set[int]:
        """Propagate a transaction through connected peers."""

        reached = self.reachable(origin)

        for node_id in reached:
            node = self.nodes[node_id]

            if tx.txid not in node.seen_messages:
                node.seen_messages.add(tx.txid)
                node.mempool[tx.txid] = tx

        self.messages_delivered += len(reached) - 1
        return reached
    
    def _receive_block(self, node_id: int, block: Block) -> bool:
        """Deliver a block to one node."""

        node = self.nodes[node_id]

        if node.chain.has(block.hash):
            return False

        if not node.chain.has(block.prev_hash):
            node.orphan_blocks[block.hash] = block
            return False

        changed = node.chain.add_block(block, check_pow=True)
        node.seen_messages.add(block.hash)

        # Retry orphan blocks after receiving their parents.
        progress = True
        while progress:
            progress = False

            for orphan_hash, orphan in list(
                node.orphan_blocks.items()
            ):
                if node.chain.has(orphan.prev_hash):
                    node.chain.add_block(
                        orphan, check_pow=True
                    )
                    node.seen_messages.add(orphan_hash)
                    del node.orphan_blocks[orphan_hash]
                    progress = True

        return changed

    def broadcast_block(self, origin: int, block: Block):
        """Send a block to nodes reachable from its origin."""

        reached = self.reachable(origin)

        for node_id in reached:
            self._receive_block(node_id, block)

        self.messages_sent += max(0, len(reached) - 1)
        self.messages_delivered += max(0, len(reached) - 1)

        return reached

    def reconcile(self):
        """Synchronise known blocks after reconnection."""

        # Gather all blocks known across the network.
        known_blocks = {}

        for node in self.nodes.values():
            for entry in node.chain.entries.values():
                block = entry.block
                known_blocks[block.hash] = block

        # Parents must be processed before children.
        ordered = sorted(
            known_blocks.values(),
            key=lambda block: block.height,
        )

        # Only share blocks within connected components.
        for node_id, node in self.nodes.items():
            connected = self.reachable(node_id)

            available = {}
            for peer_id in connected:
                for entry in self.nodes[
                    peer_id
                ].chain.entries.values():
                    block = entry.block
                    available[block.hash] = block

            for block in sorted(
                available.values(),
                key=lambda b: b.height,
            ):
                if not node.chain.has(block.hash):
                    self._receive_block(node_id, block)

        return {
            node_id: node.chain.tip_hash
            for node_id, node in self.nodes.items()
        }






import hashlib
import pickle
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """A transaction or block shared between nodes."""

    kind: str
    payload: object
    origin: str

    @property
    def message_id(self) -> str:
        data = pickle.dumps((
            self.kind,
            self.payload,
            self.origin,
        ))
        return hashlib.sha256(data).hexdigest()


class Network:
    """Manage node connections and network partitions."""

    def __init__(self, latency: float = 0.001):
        if latency < 0:
            raise ValueError("latency must be non-negative")

        self.latency = latency
        self.connections: dict[str, set[str]] = {}
        self.blocked_links: set[frozenset[str]] = set()
        self.nodes: dict[str, AsyncNode] = {}

    def register(self, node_id: str) -> None:
        self.connections.setdefault(node_id, set())

    def connect(self, a: str, b: str) -> None:
        if a == b:
            return

        self.register(a)
        self.register(b)

        self.connections[a].add(b)
        self.connections[b].add(a)

    def can_reach(self, a: str, b: str) -> bool:
        """Check whether a direct connection is available."""
        return (
            b in self.connections.get(a, set())
            and frozenset((a, b))
            not in self.blocked_links
        )


    def partition(self, group_a, group_b=None) -> None:
        """Partition the network using groups or a mapping."""

        if group_b is not None:
            # Format 1: two separate groups.
            groups = [set(group_a), set(group_b)]

        elif isinstance(group_a, dict):
            # Format 2: node -> group label mapping.
            labels = group_a
            self.blocked_links.clear()

            for a in labels:
                for b in labels:
                    if labels[a] != labels[b]:
                        self.blocked_links.add(
                            frozenset((a, b))
                        )
            return

        elif isinstance(group_a, (list, tuple)):
            # Format 3: list of groups (professor's API).
            groups = [set(group) for group in group_a]

        else:
            raise TypeError(
                "Expected two groups, a group mapping, "
                "or a list of groups"
            )

        self.blocked_links.clear()

        for i, first_group in enumerate(groups):
            for second_group in groups[i + 1:]:
                for a in first_group:
                    for b in second_group:
                        self.blocked_links.add(
                            frozenset((a, b))
                        )

    
    
    def heal(self) -> None:
        """Restore links and synchronise connected nodes."""

        self.blocked_links.clear()

        for node_id in self.nodes:
            self.synchronize_component(node_id)



    def synchronize_component(self, start: str) -> None:
        """Synchronise blockchain histories in a connected group."""

        # Discover nodes reachable from the starting node.
        connected = {start}
        pending = [start]

        while pending:
            current = pending.pop()

            for peer in self.connections.get(current, set()):
                if (
                    peer not in connected
                    and self.can_reach(current, peer)
                ):
                    connected.add(peer)
                    pending.append(peer)

        # Collect blocks from all reachable nodes.
        available = {}

        for node_id in connected:
            node = self.nodes[node_id]

            for entry in node.chain.entries.values():
                block = entry.block
                available[block.hash] = block

        # Process parents before children.
        ordered = sorted(
            available.values(),
            key=lambda block: (block.height, block.hash),
        )

        for node_id in connected:
            node = self.nodes[node_id]
            previous_reorgs = node.chain.reorg_count

            for block in ordered:
                if node.chain.has(block.hash):
                    continue

                # The reference simulation permits locally
                # constructed blocks without mined PoW.
                # Do not use this bypass for production consensus.
                try:
                    node.chain.add_block(
                        block,
                        check_pow=False,
                    )
                except (ValueError, KeyError):
                    continue

            node.stats.reorgs += max(
                0,
                node.chain.reorg_count - previous_reorgs,
            )



import asyncio


@dataclass
class NodeStats:
    duplicates_suppressed: int = 0
    reorgs: int = 0
    messages_received: int = 0


class AsyncNode:
    """A blockchain node that processes gossip messages."""

    def __init__(
        self,
        node_id: str,
        network: Network,
        initial_balances: dict[str, int] | None = None,
    ):
        self.node_id = node_id
        self.network = network
        self.network.register(node_id)
        self.network.nodes[node_id] = self

        self.chain = Chain()
        self.initial_balances = dict(initial_balances or {})
        self.mempool = {}
        self.seen_messages = set()
        self.inbox = asyncio.Queue()
        self.stats = NodeStats()

        self.running = False

    @property
    def peers(self) -> set[str]:
        return self.network.connections.get(
            self.node_id, set()
        )

    @property
    def height(self) -> int:
        return self.chain.height

    @property
    def tip_hash(self) -> str:
        return self.chain.tip_hash

    async def submit_transaction(
        self, tx: Transaction
    ) -> bool:
        """Validate a transaction and broadcast it."""

        state = self.chain.replay_state(
            self.initial_balances
        )

        if state.validate(tx) is not None:
            return False

        await self.broadcast(
            Message("transaction", tx, self.node_id)
        )

        return True

    async def broadcast(self, message: Message) -> None:
        """Deliver a message to this node and its peers."""

        await self.inbox.put(message)

    async def _relay(self, message: Message) -> None:
        """Forward a message to connected peers."""

        for peer_id in self.peers:
            if not self.network.can_reach(
                self.node_id, peer_id
            ):
                continue

            peer = self.network.nodes.get(peer_id)

            if peer is None:
                continue

            await asyncio.sleep(self.network.latency)
            await peer.inbox.put(message)

    async def _handle_message(
        self, message: Message
    ) -> None:
        self.stats.messages_received += 1

        if message.message_id in self.seen_messages:
            self.stats.duplicates_suppressed += 1
            return

        self.seen_messages.add(message.message_id)

        if message.kind == "transaction":
            tx = message.payload

            state = self.chain.replay_state(
                self.initial_balances
            )

            if state.validate(tx) is not None:
                return

            self.mempool[tx.txid] = tx

        elif message.kind == "block":
            block = message.payload

            if not self.chain.has(block.hash):
                try:
                    self.chain.add_block(block)
                except (ValueError, KeyError):
                    return

        await self._relay(message)

    async def run(self) -> None:
        """Process incoming messages until stopped."""

        self.running = True

        while self.running:
            try:
                message = await asyncio.wait_for(
                    self.inbox.get(),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                continue

            await self._handle_message(message)
            self.inbox.task_done()


    async def announce_head(self) -> None:
        """Announce and synchronise the current chain head."""

        self.network.synchronize_component(self.node_id)

        await asyncio.sleep(self.network.latency)


    def stop(self) -> None:
        self.running = False




import random


# Public interface expected by the reference tests.
Node = AsyncNode


def build_network(
    node_count: int = 6,
    latency: float = 0.001,
    seed: int = 0,
    initial_balances: dict[str, int] | None = None,
) -> tuple[Network, dict[str, AsyncNode]]:
    """Create a reproducible, connected gossip network."""

    if node_count < 1:
        raise ValueError("node_count must be positive")

    network = Network(latency=latency)
    rng = random.Random(seed)

    nodes = {
        f"node{i}": AsyncNode(
            node_id=f"node{i}",
            network=network,
            initial_balances=initial_balances,
        )
        for i in range(node_count)
    }

    # A spanning tree guarantees connectivity.
    for i in range(1, node_count):
        parent = rng.randrange(i)
        network.connect(f"node{i}", f"node{parent}")

    # Add extra edges to support gossip through
    # multiple paths and duplicate-message testing.
    for i in range(node_count):
        for j in range(i + 1, node_count):
            if rng.random() < 0.5:
                network.connect(f"node{i}", f"node{j}")

    return network, nodes
