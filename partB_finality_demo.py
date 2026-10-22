
from consensus.pos import (
    BeaconState,
    Checkpoint,
    Attestation,
)


def main():
    state = BeaconState(validator_count=9)
    previous = state.genesis_checkpoint

    print("PART B - CASPER FFG FINALITY")
    print("=" * 45)

    for epoch in range(1, 4):
        checkpoint = Checkpoint(
            epoch, f"root-{epoch}"
        )

        for validator in range(7):
            state.attest(
                Attestation(
                    validator,
                    previous,
                    checkpoint,
                )
            )

        result = state.process_epoch(epoch)

        print(f"\nEpoch {epoch}")
        print(f"Justified: {result['justified']}")
        print(f"Newly finalised: {result['finalized']}")
        print(f"Current finalised: {state.finalized}")

        previous = checkpoint


if __name__ == "__main__":
    main()

