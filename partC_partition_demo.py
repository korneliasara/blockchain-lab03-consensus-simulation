
"""Part C - Network partition and blockchain reorganisation."""

import csv

from consensus.chain import make_block
from consensus.network import GossipNetwork
from consensus.pow import mine


def mine_blocks(network, node_id, count, start_time):
    """Mine and broadcast blocks within a network partition."""
    for i in range(count):
        chain = network.nodes[node_id].chain

        candidate = make_block(
            chain,
            miner=f"miner-{node_id}",
            timestamp=float(start_time + i),
        )

        block = mine(candidate)
        network.broadcast_block(node_id, block)


def main():
    network = GossipNetwork(6)
    network.connect_all()

    group_a = {0, 1, 2}
    group_b = {3, 4, 5}

    print("PART C - NETWORK PARTITION SIMULATION")
    print("=" * 55)

    network.partition(group_a, group_b)

    print("\n1. Network partitioned")
    print("Group A:", sorted(group_a))
    print("Group B:", sorted(group_b))

    mine_blocks(network, 0, 3, 10)
    mine_blocks(network, 3, 5, 20)

    print("\n2. Before reconnection")

    for node_id, node in network.nodes.items():
        print(
            f"Node {node_id}: "
            f"height={node.chain.height}, "
            f"work={node.chain.total_work}"
        )

    network.reconnect_all()
    network.reconcile()

    print("\n3. After reconnection")

    rows = []

    for node_id, node in network.nodes.items():
        print(
            f"Node {node_id}: "
            f"height={node.chain.height}, "
            f"reorgs={node.chain.reorg_count}, "
            f"depths={node.chain.reorg_depths}"
        )

        rows.append([
            node_id,
            node.chain.height,
            node.chain.total_work,
            node.chain.reorg_count,
            ";".join(map(str, node.chain.reorg_depths)),
            node.chain.tip_hash,
        ])

    all_tips = {
        node.chain.tip_hash
        for node in network.nodes.values()
    }

    print("\nAll nodes agree:", len(all_tips) == 1)
    print("Winning height:", network.nodes[0].chain.height)

    with open(
        "partC_partition_results.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "node", "height", "cumulative_work",
            "reorg_count", "reorg_depths", "tip_hash"
        ])
        writer.writerows(rows)

    print("\nResults saved to partC_partition_results.csv")


if __name__ == "__main__":
    main()
