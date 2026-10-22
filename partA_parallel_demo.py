
from time import perf_counter

from consensus.chain import Chain, make_block
from consensus.pow import mine_parallel


def main():
    chain = Chain()

    print("PART A - PARALLEL PROOF OF WORK")
    print("=" * 45)

    for workers in (1, 2, 4):
        block = make_block(
            chain,
            miner="miner",
            timestamp=1.0,
        )

        start = perf_counter()
        mined = mine_parallel(block, workers=workers)
        elapsed = perf_counter() - start

        print(f"\nWorkers: {workers}")
        print(f"Valid PoW: {mined.is_valid_pow()}")
        print(f"Winning nonce: {mined.nonce}")
        print(f"Elapsed time: {elapsed:.4f} seconds")


if __name__ == "__main__":
    main()
