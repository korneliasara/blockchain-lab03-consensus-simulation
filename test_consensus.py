
import pytest

from consensus.chain import Transaction, State, sha256d


def test_valid_transaction():
    state = State({"alice": 100})

    tx = Transaction(
        sender="alice",
        recipient="bob",
        amount=30,
        nonce=0,
    )

    state.apply(tx)

    assert state.balance_of("alice") == 70
    assert state.balance_of("bob") == 30
    assert state.nonce_of("alice") == 1


def test_insufficient_balance():
    state = State({"alice": 10})

    tx = Transaction("alice", "bob", 30, nonce=0)

    assert state.validate(tx) == "insufficient balance"


def test_transaction_fee():
    state = State({"alice": 100})

    tx = Transaction("alice", "bob", 30, nonce=0, fee=5)

    state.apply(tx)

    assert state.balance_of("alice") == 65
    assert state.balance_of("bob") == 30


def test_repeated_nonce_rejected():
    state = State({"alice": 100})

    tx = Transaction("alice", "bob", 10, nonce=0)

    state.apply(tx)

    assert state.validate(tx) is not None


def test_skipped_nonce_rejected():
    state = State({"alice": 100})

    tx = Transaction("alice", "bob", 10, nonce=2)

    assert state.validate(tx) is not None


def test_transaction_id_deterministic():
    tx = Transaction("alice", "bob", 10, nonce=0)

    assert tx.txid == tx.txid
    assert len(tx.txid) == 64




from consensus.chain import (
    Block, Chain, make_block, genesis_block
)


def test_genesis_block():
    chain = Chain()

    assert chain.height == 0
    assert chain.tip.prev_hash == "00" * 32


def test_block_hash_changes_with_transaction():
    chain = Chain()

    empty_block = make_block(chain, timestamp=1.0)

    tx = Transaction("alice", "bob", 10, nonce=0)
    filled_block = make_block(
        chain, txs=(tx,), timestamp=1.0
    )

    assert empty_block.hash != filled_block.hash


def test_block_added():
    chain = Chain()
    block = make_block(chain, timestamp=1.0)

    assert chain.add_block(block, check_pow=False)
    assert chain.height == 1


def test_unknown_parent_rejected():
    chain = Chain()

    block = Block(
        height=1,
        prev_hash="ff" * 32,
        timestamp=1.0,
    )

    with pytest.raises(KeyError):
        chain.add_block(block, check_pow=False)


def test_equal_work_does_not_replace_tip():
    chain = Chain()

    first = make_block(chain, miner="A", timestamp=1.0)
    chain.add_block(first, check_pow=False)

    competitor = Block(
        height=1,
        prev_hash=chain.genesis_hash,
        timestamp=2.0,
        miner="B",
    )

    assert not chain.add_block(
        competitor, check_pow=False
    )

    assert chain.tip_hash == first.hash
    assert chain.has(competitor.hash)


def test_heavier_fork_wins():
    chain = Chain()

    first = make_block(chain, miner="A", timestamp=1.0)
    chain.add_block(first, check_pow=False)

    competitor = Block(
        height=1,
        prev_hash=chain.genesis_hash,
        timestamp=2.0,
        miner="B",
    )

    chain.add_block(competitor, check_pow=False)

    second = Block(
        height=2,
        prev_hash=competitor.hash,
        timestamp=3.0,
        miner="B",
    )

    chain.add_block(second, check_pow=False)

    assert chain.tip_hash == second.hash
    assert chain.reorg_count == 1
    assert chain.reorg_depths[-1] == 1


def test_replay_state():
    chain = Chain()

    tx = Transaction("alice", "bob", 10, nonce=0)

    block = make_block(
        chain,
        txs=(tx,),
        miner="miner1",
        timestamp=1.0,
    )

    chain.add_block(block, check_pow=False)

    state = chain.replay_state({"alice": 100})

    assert state.balance_of("alice") == 90
    assert state.balance_of("bob") == 10
    assert state.balance_of("miner1") == 50



from consensus.pow import (
    target_from_difficulty,
    difficulty_from_target,
    retarget,
    mine_range,
    mine,
)


def test_higher_difficulty_lower_target():
    assert target_from_difficulty(2) < target_from_difficulty(1)


def test_difficulty_roundtrip():
    target = target_from_difficulty(4)
    assert difficulty_from_target(target) == 4


def test_mining_produces_valid_block():
    chain = Chain()
    block = make_block(chain, miner="alice", timestamp=1.0)

    mined = mine(block)

    assert mined.is_valid_pow()
    assert int(mined.hash, 16) < mined.target


def test_retarget_directions():
    assert retarget(1000, 300, 600) == 2000
    assert retarget(1000, 1200, 600) == 500


def test_retarget_clamp():
    assert retarget(1000, 6, 600) == 4000
    assert retarget(1000, 60000, 600) == 250


def test_retarget_minimum_difficulty():
    assert retarget(1, 10000, 600) == 1



from consensus.pow import mine_parallel


def test_parallel_mining():
    chain = Chain()
    block = make_block(
        chain, miner="parallel-miner", timestamp=1.0
    )

    mined = mine_parallel(block, workers=2)

    assert mined.is_valid_pow()
    assert mined.prev_hash == chain.tip_hash


def test_parallel_mining_single_worker():
    chain = Chain()
    block = make_block(
        chain, miner="single-worker", timestamp=1.0
    )

    mined = mine_parallel(block, workers=1)

    assert mined.is_valid_pow()


def test_parallel_mining_invalid_workers():
    chain = Chain()
    block = make_block(chain, timestamp=1.0)

    with pytest.raises(ValueError):
        mine_parallel(block, workers=0)


def test_strided_nonce_search():
    chain = Chain()
    block = make_block(chain, timestamp=1.0)

    even = mine_range(block, 0, 200000, 2)
    odd = mine_range(block, 1, 200000, 2)

    assert even is not None or odd is not None




from consensus.pos import (
    Checkpoint,
    Attestation,
    Validator,
    BeaconState,
    GWEI,
)


def test_validator_initial_balance():
    validator = Validator(index=0)

    assert validator.balance == 32 * GWEI
    assert validator.is_active


def test_validator_effective_balance():
    validator = Validator(index=0, balance=40 * GWEI)

    assert validator.effective_balance == 32 * GWEI


def test_six_of_nine_not_enough():
    state = BeaconState(validator_count=9)

    target = Checkpoint(1, "block-1")

    for validator in range(6):
        state.attest(
            Attestation(
                validator,
                state.genesis_checkpoint,
                target,
            )
        )

    result = state.process_epoch(1)

    assert result["justified"] is None


def test_seven_of_nine_justifies():
    state = BeaconState(validator_count=9)

    target = Checkpoint(1, "block-1")

    for validator in range(7):
        state.attest(
            Attestation(
                validator,
                state.genesis_checkpoint,
                target,
            )
        )

    result = state.process_epoch(1)

    assert result["justified"] == target


def test_unjustified_source_rejected():
    state = BeaconState(validator_count=9)

    source = Checkpoint(1, "unknown-block")
    target = Checkpoint(2, "block-2")

    for validator in range(9):
        state.attest(
            Attestation(validator, source, target)
        )

    result = state.process_epoch(2)

    assert result["justified"] is None





def test_casper_finalization_two_epochs():
    state = BeaconState(validator_count=9)

    genesis = state.genesis_checkpoint
    cp1 = Checkpoint(1, "root-1")
    cp2 = Checkpoint(2, "root-2")

    # Epoch 1: enough validators justify cp1.
    for i in range(7):
        state.attest(Attestation(i, genesis, cp1))

    result1 = state.process_epoch(1)

    assert result1["justified"] == cp1
    assert result1["finalized"] is None

    # Epoch 2: justify cp2 using cp1 as source.
    for i in range(7):
        state.attest(Attestation(i, cp1, cp2))

    result2 = state.process_epoch(2)

    assert result2["justified"] == cp2
    assert result2["finalized"] == cp1
    assert state.finalized == cp1


def test_finalization_requires_successor():
    state = BeaconState(validator_count=9)

    genesis = state.genesis_checkpoint
    cp1 = Checkpoint(1, "root-1")

    for i in range(7):
        state.attest(Attestation(i, genesis, cp1))

    state.process_epoch(1)

    assert state.finalized == genesis




from consensus.pos import (
    is_double_vote,
    is_surround_vote,
    find_violations,
)


def test_double_vote_detection():
    source = Checkpoint(0, "genesis")

    a = Attestation(0, source, Checkpoint(1, "A"))
    b = Attestation(0, source, Checkpoint(1, "B"))

    assert is_double_vote(a, b)


def test_surround_vote_detection():
    a = Attestation(
        0, Checkpoint(1, "A"), Checkpoint(5, "B")
    )
    b = Attestation(
        0, Checkpoint(2, "C"), Checkpoint(4, "D")
    )

    assert is_surround_vote(a, b)


def test_single_validator_slashing():
    state = BeaconState(64)
    genesis = state.genesis_checkpoint

    state.attest(Attestation(0, genesis, Checkpoint(1, "A")))
    state.attest(Attestation(0, genesis, Checkpoint(1, "B")))

    result = state.process_epoch(1)

    assert len(result["slashed"]) == 1
    assert state.validators[0].slashed

    loss = (
        32 * GWEI - state.validators[0].balance
    ) / GWEI

    assert 2.3 < loss < 2.5


def test_validator_not_slashed_twice():
    state = BeaconState(64)
    genesis = state.genesis_checkpoint

    state.attest(Attestation(0, genesis, Checkpoint(1, "A")))
    state.attest(Attestation(0, genesis, Checkpoint(1, "B")))

    state.process_epoch(1)
    balance_after_first = state.validators[0].balance

    state.process_epoch(2)

    assert len(state.slashings) == 1
    assert state.validators[0].balance == balance_after_first


def test_coordinated_slashing():
    state = BeaconState(64)
    genesis = state.genesis_checkpoint

    for i in range(20):
        state.attest(
            Attestation(i, genesis, Checkpoint(1, "A"))
        )
        state.attest(
            Attestation(i, genesis, Checkpoint(1, "B"))
        )

    result = state.process_epoch(1)

    assert len(result["slashed"]) == 20

    loss = (
        32 * GWEI - state.validators[0].balance
    ) / GWEI

    assert 29.0 < loss < 30.0



def test_inactivity_grace_period():
    state = BeaconState(9)

    for epoch in range(1, 5):
        result = state.process_epoch(epoch)
        assert result["inactivity_leak"] == 0

    assert all(v.balance == 32 * GWEI for v in state.validators)


def test_inactivity_penalises_absent_only():
    state = BeaconState(9)
    genesis = state.genesis_checkpoint

    target = Checkpoint(5, "root-5")

    for index in range(3):
        state.attest(
            Attestation(index, genesis, target)
        )

    result = state.process_epoch(5)

    assert result["inactivity_leak"] > 0

    for index in range(3):
        assert state.validators[index].balance == 32 * GWEI

    for index in range(3, 9):
        assert state.validators[index].balance < 32 * GWEI


def test_inactivity_stops_after_finality():
    state = BeaconState(9)
    genesis = state.genesis_checkpoint

    cp1 = Checkpoint(1, "root-1")
    cp2 = Checkpoint(2, "root-2")

    for i in range(7):
        state.attest(Attestation(i, genesis, cp1))

    state.process_epoch(1)

    for i in range(7):
        state.attest(Attestation(i, cp1, cp2))

    state.process_epoch(2)

    assert state.finalized == cp1

    result = state.process_epoch(5)

    assert result["inactivity_leak"] == 0






from consensus.network import GossipNetwork


def test_network_initialization():
    network = GossipNetwork(5)
    assert len(network.nodes) == 5


def test_network_connections():
    network = GossipNetwork(3)

    network.connect(0, 1)

    assert 1 in network.nodes[0].peers
    assert 0 in network.nodes[1].peers


def test_gossip_reaches_connected_nodes():
    network = GossipNetwork(4)

    network.connect(0, 1)
    network.connect(1, 2)
    network.connect(2, 3)

    tx = Transaction("alice", "bob", 10, nonce=0)

    reached = network.broadcast_transaction(0, tx)

    assert reached == {0, 1, 2, 3}

    for node in network.nodes.values():
        assert tx.txid in node.mempool


def test_partition_blocks_gossip():
    network = GossipNetwork(6)
    network.connect_all()

    network.partition({0, 1, 2}, {3, 4, 5})

    tx = Transaction("alice", "bob", 10, nonce=0)

    reached = network.broadcast_transaction(0, tx)

    assert reached == {0, 1, 2}

    for i in (3, 4, 5):
        assert tx.txid not in network.nodes[i].mempool


def test_network_reconnection():
    network = GossipNetwork(4)
    network.connect_all()

    network.partition({0, 1}, {2, 3})
    assert network.reachable(0) == {0, 1}

    network.reconnect_all()
    assert network.reachable(0) == {0, 1, 2, 3}




def test_block_gossip():
    network = GossipNetwork(4)
    network.connect_all()

    block = make_block(
        network.nodes[0].chain,
        miner="A",
        timestamp=1.0,
    )

    mined = mine(block)
    reached = network.broadcast_block(0, mined)

    assert reached == {0, 1, 2, 3}

    for node in network.nodes.values():
        assert node.chain.tip_hash == mined.hash


def test_partition_creates_competing_branches():
    network = GossipNetwork(4)
    network.connect_all()
    network.partition({0, 1}, {2, 3})

    block_a = mine(make_block(
        network.nodes[0].chain,
        miner="A",
        timestamp=1.0,
    ))

    block_b = mine(make_block(
        network.nodes[2].chain,
        miner="B",
        timestamp=2.0,
    ))

    network.broadcast_block(0, block_a)
    network.broadcast_block(2, block_b)

    assert network.nodes[0].chain.tip_hash == block_a.hash
    assert network.nodes[2].chain.tip_hash == block_b.hash
    assert block_a.hash != block_b.hash


def test_reconnection_selects_heavier_chain():
    network = GossipNetwork(4)
    network.connect_all()
    network.partition({0, 1}, {2, 3})

    block_a = mine(make_block(
        network.nodes[0].chain,
        miner="A",
        timestamp=1.0,
    ))
    network.broadcast_block(0, block_a)

    for height in range(1, 3):
        block_b = mine(make_block(
            network.nodes[2].chain,
            miner="B",
            timestamp=float(height + 10),
        ))
        network.broadcast_block(2, block_b)

    network.reconnect_all()
    network.reconcile()

    expected = block_b.hash

    assert all(
        node.chain.tip_hash == expected
        for node in network.nodes.values()
    )


def test_reorganization_recorded():
    network = GossipNetwork(4)
    network.connect_all()
    network.partition({0, 1}, {2, 3})

    block_a = mine(make_block(
        network.nodes[0].chain,
        miner="A",
        timestamp=1.0,
    ))
    network.broadcast_block(0, block_a)

    for height in range(1, 3):
        block_b = mine(make_block(
            network.nodes[2].chain,
            miner="B",
            timestamp=float(height + 10),
        ))
        network.broadcast_block(2, block_b)

    network.reconnect_all()
    network.reconcile()

    assert network.nodes[0].chain.reorg_count >= 1
    assert 1 in network.nodes[0].chain.reorg_depths




def test_orphan_block_stored():
    network = GossipNetwork(2)
    network.connect_all()

    chain = network.nodes[0].chain

    parent = mine(make_block(
        chain,
        miner="miner",
        timestamp=1.0,
    ))

    chain.add_block(parent)

    child = mine(make_block(
        chain,
        miner="miner",
        timestamp=2.0,
    ))

    # Node 1 receives the child before the parent.
    network._receive_block(1, child)

    assert child.hash in network.nodes[1].orphan_blocks
    assert network.nodes[1].chain.height == 0


def test_orphan_resolved_after_parent():
    network = GossipNetwork(2)
    network.connect_all()

    chain = network.nodes[0].chain

    parent = mine(make_block(
        chain,
        miner="miner",
        timestamp=1.0,
    ))
    chain.add_block(parent)

    child = mine(make_block(
        chain,
        miner="miner",
        timestamp=2.0,
    ))

    network._receive_block(1, child)
    network._receive_block(1, parent)

    assert network.nodes[1].chain.has(child.hash)
    assert network.nodes[1].chain.height == 2
    assert len(network.nodes[1].orphan_blocks) == 0


def test_duplicate_block_ignored():
    network = GossipNetwork(2)
    network.connect_all()

    block = mine(make_block(
        network.nodes[0].chain,
        timestamp=1.0,
    ))

    network.broadcast_block(0, block)
    height_before = network.nodes[1].chain.height

    network.broadcast_block(0, block)

    assert network.nodes[1].chain.height == height_before
    assert len(network.nodes[1].chain.entries) == 2


def test_partition_reconciliation_preserves_blocks():
    network = GossipNetwork(4)
    network.connect_all()
    network.partition({0, 1}, {2, 3})

    block_a = mine(make_block(
        network.nodes[0].chain,
        miner="A",
        timestamp=1.0,
    ))

    block_b = mine(make_block(
        network.nodes[2].chain,
        miner="B",
        timestamp=2.0,
    ))

    network.broadcast_block(0, block_a)
    network.broadcast_block(2, block_b)

    network.reconnect_all()
    network.reconcile()

    for node in network.nodes.values():
        assert node.chain.has(block_a.hash)
        assert node.chain.has(block_b.hash)





from consensus.network import Message, Network


def test_message_id_deterministic():
    msg = Message("transaction", "example", "node0")

    assert msg.message_id == msg.message_id
    assert len(msg.message_id) == 64


def test_async_network_connections():
    network = Network()

    network.connect("node0", "node1")

    assert network.can_reach("node0", "node1")
    assert network.can_reach("node1", "node0")


def test_async_network_partition_and_heal():
    network = Network()

    network.connect("node0", "node1")
    network.connect("node1", "node2")

    network.partition(
        {"node0", "node1"},
        {"node2"},
    )

    assert network.can_reach("node0", "node1")
    assert not network.can_reach("node1", "node2")

    network.heal()

    assert network.can_reach("node1", "node2")





import asyncio

from consensus.network import AsyncNode


@pytest.mark.asyncio
async def test_async_transaction_propagation():
    network = Network(latency=0.001)

    nodes = {
        f"node{i}": AsyncNode(
            f"node{i}",
            network,
            {"alice": 100},
        )
        for i in range(3)
    }

    network.connect("node0", "node1")
    network.connect("node1", "node2")

    tasks = [
        asyncio.create_task(node.run())
        for node in nodes.values()
    ]

    try:
        tx = Transaction(
            "alice", "bob", 10, nonce=0
        )

        assert await nodes[
            "node0"
        ].submit_transaction(tx)

        await asyncio.sleep(0.2)

        assert all(
            tx.txid in node.mempool
            for node in nodes.values()
        )

    finally:
        for node in nodes.values():
            node.stop()

        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks, return_exceptions=True
        )


@pytest.mark.asyncio
async def test_async_duplicate_suppression():
    network = Network(latency=0.001)

    nodes = {
        f"node{i}": AsyncNode(
            f"node{i}",
            network,
            {"alice": 100},
        )
        for i in range(3)
    }

    network.connect("node0", "node1")
    network.connect("node1", "node2")
    network.connect("node2", "node0")

    tasks = [
        asyncio.create_task(node.run())
        for node in nodes.values()
    ]

    try:
        tx = Transaction(
            "alice", "bob", 10, nonce=0
        )

        await nodes["node0"].submit_transaction(tx)
        await asyncio.sleep(0.2)

        assert sum(
            node.stats.duplicates_suppressed
            for node in nodes.values()
        ) > 0

    finally:
        for node in nodes.values():
            node.stop()

        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks, return_exceptions=True
        )


@pytest.mark.asyncio
async def test_async_invalid_transaction_rejected():
    network = Network(latency=0.001)

    nodes = {
        f"node{i}": AsyncNode(
            f"node{i}",
            network,
            {"alice": 10},
        )
        for i in range(3)
    }

    network.connect("node0", "node1")
    network.connect("node1", "node2")

    tasks = [
        asyncio.create_task(node.run())
        for node in nodes.values()
    ]

    try:
        tx = Transaction(
            "alice", "bob", 1000000, nonce=0
        )

        accepted = await nodes[
            "node0"
        ].submit_transaction(tx)

        await asyncio.sleep(0.1)

        assert not accepted
        assert all(
            len(node.mempool) == 0
            for node in nodes.values()
        )

    finally:
        for node in nodes.values():
            node.stop()

        for task in tasks:
            task.cancel()

        await asyncio.gather(
            *tasks, return_exceptions=True
        )

