
"""Part B - Correlated slashing experiment."""

import csv

from consensus.pos import (
    Attestation,
    BeaconState,
    Checkpoint,
    GWEI,
)


def run_scenario(offender_count):
    state = BeaconState(validator_count=64)
    genesis = state.genesis_checkpoint

    checkpoint_a = Checkpoint(1, "chain-A")
    checkpoint_b = Checkpoint(1, "chain-B")

    # All validators vote for chain A.
    for i in range(64):
        state.attest(Attestation(i, genesis, checkpoint_a))

    # The offenders also vote for chain B.
    for i in range(offender_count):
        state.attest(Attestation(i, genesis, checkpoint_b))

    result = state.process_epoch(1)

    initial_balance = 32 * GWEI
    final_balance = state.validators[0].balance

    loss = (initial_balance - final_balance) / GWEI

    return loss, len(result["slashed"])


def main():
    print("PART B - CORRELATED SLASHING")
    print("=" * 55)
    print(f"{'Offenders':<15}{'Loss per validator (ETH)':<25}")

    rows = []

    for count in [1, 5, 10, 20, 30]:
        loss, slashed = run_scenario(count)
        rows.append((count, loss))

        print(f"{count:<15}{loss:<25.4f}")

    with open(
        "partB_slashing_results.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["offenders", "loss_eth"])
        writer.writerows(rows)

    print("\nResults saved to partB_slashing_results.csv")


if __name__ == "__main__":
    main()
