
"""Part B - Inactivity leak and finality recovery."""

import csv
from consensus.pos import (
    BeaconState,
    Checkpoint,
    Attestation,
)


def main():
    state = BeaconState(validator_count=64)
    online = list(range(24))

    rows = []

    print("PART B - INACTIVITY LEAK")
    print("=" * 65)
    print("Epoch | Voting share | Leaked ETH | Finalized epoch")

    for epoch in range(1, 101):
        source = state.current_justified
        target = Checkpoint(epoch, f"root-{epoch}")

        for index in online:
            state.attest(
                Attestation(index, source, target)
            )

        voting_balance = sum(
            state.validators[i].effective_balance
            for i in online
        )

        total_balance = state.total_active_balance
        voting_share = voting_balance / total_balance

        result = state.process_epoch(epoch)

        leaked_eth = result["inactivity_leak"] / 10**9
        finalized_epoch = state.finalized.epoch

        rows.append((
            epoch,
            voting_share * 100,
            leaked_eth,
            finalized_epoch,
        ))

        if (
            epoch == 1
            or epoch % 10 == 0
            or result["justified"] is not None
            or result["finalized"] is not None
        ):
            print(
                f"{epoch:5} | "
                f"{voting_share*100:11.2f}% | "
                f"{leaked_eth:10.4f} | "
                f"{finalized_epoch:15}"
            )

    with open(
        "partB_inactivity_results.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "epoch",
            "voting_share_percent",
            "leaked_eth",
            "finalized_epoch",
        ])
        writer.writerows(rows)

    print("\nResults saved successfully.")


if __name__ == "__main__":
    main()
