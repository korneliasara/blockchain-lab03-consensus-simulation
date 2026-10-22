
import time
import multiprocessing as mp

from bonus_E2_miner import PersistentMiner

TARGET = (1 << 256) // 100_000


def main():
    print("E2 - WORKER PERSISTENCE DIAGNOSTICS")

    for count in [1, 2, 4]:
        print(f"\nWorkers: {count}")

        with PersistentMiner(workers=count) as miner:
            before = [p["pid"] for p in miner.worker_status()]

            times = []

            for i in range(10):
                header = f"diagnostic-{i}".encode()
                result = miner.mine(header, TARGET)
                times.append(result["elapsed"])

            after = [p["pid"] for p in miner.worker_status()]

            print("Worker PIDs:", before)
            print("Workers reused:", before == after)
            print("Workers alive:", all(
                p["alive"] for p in miner.worker_status()
            ))
            print("Mean time:", round(sum(times) / len(times), 4))
            print("Total time:", round(sum(times), 4))


if __name__ == "__main__":
    mp.freeze_support()
    main()
