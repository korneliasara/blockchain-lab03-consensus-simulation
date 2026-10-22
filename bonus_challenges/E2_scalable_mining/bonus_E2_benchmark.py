
"""Bonus E2 - Persistent worker mining benchmark."""

import csv
import statistics
import math
from pathlib import Path

import matplotlib.pyplot as plt

from bonus_E2_miner import PersistentMiner

OUTPUT = Path(__file__).resolve().parent
BLOCK_COUNT = 100
TARGET = (1 << 256) // 100_000
WORKER_COUNTS = [1, 2, 4]


def benchmark(workers):
    times = []
    rows = []

    print(f"\nBenchmark: {workers} worker(s)")

    # Workers are created ONCE for the entire experiment.
    with PersistentMiner(workers=workers) as miner:
        for number in range(BLOCK_COUNT):
            header = f"E2-benchmark-block-{number}".encode()
            result = miner.mine(header, TARGET)

            elapsed = result["elapsed"]
            times.append(elapsed)

            rows.append([
                workers,
                number,
                elapsed,
                result["nonce"],
                result["attempts"],
            ])

            if (number + 1) % 20 == 0:
                print(f"  Completed {number + 1} blocks")

    mean = statistics.mean(times)
    median = statistics.median(times)
    stdev = statistics.stdev(times)

    return {
        "workers": workers,
        "mean": mean,
        "median": median,
        "stdev": stdev,
        "median_mean": median / mean,
        "stdev_mean": stdev / mean,
        "rows": rows,
        "times": times,
    }


def save_results(results):
    with open(
        OUTPUT / "bonus_E2_block_times.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "workers", "block", "seconds",
            "nonce", "attempts",
        ])

        for result in results:
            writer.writerows(result["rows"])

    baseline = results[0]["mean"]

    with open(
        OUTPUT / "bonus_E2_summary.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "workers", "mean_seconds",
            "median_seconds", "stdev_seconds",
            "median_mean", "stdev_mean", "speedup",
        ])

        for result in results:
            writer.writerow([
                result["workers"],
                result["mean"],
                result["median"],
                result["stdev"],
                result["median_mean"],
                result["stdev_mean"],
                baseline / result["mean"],
            ])


def create_charts(results):
    workers = [r["workers"] for r in results]
    baseline = results[0]["mean"]

    actual_speedup = [
        baseline / r["mean"] for r in results
    ]

    plt.figure(figsize=(9, 5))
    plt.plot(
        workers, workers,
        "--", marker="o", label="Ideal speed-up",
    )
    plt.plot(
        workers, actual_speedup,
        marker="o", label="Measured speed-up",
    )

    plt.xlabel("Number of workers")
    plt.ylabel("Speed-up relative to one worker")
    plt.title("Persistent Parallel Mining - Speed-up")
    plt.xticks(workers)
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        OUTPUT / "bonus_E2_speedup.png", dpi=200
    )
    plt.close()

    four_worker_times = results[-1]["times"]

    plt.figure(figsize=(9, 5))
    plt.hist(
        four_worker_times,
        bins=15,
        edgecolor="black",
    )
    plt.xlabel("Block mining time (seconds)")
    plt.ylabel("Number of blocks")
    plt.title("Persistent Mining - 4 Worker Block Times")
    plt.grid(alpha=0.2)
    plt.tight_layout()

    plt.savefig(
        OUTPUT / "bonus_E2_interval_histogram.png",
        dpi=200,
    )
    plt.close()


def main():
    print("BONUS E2 - SCALABLE MINING BENCHMARK")
    print("=" * 60)

    results = [
        benchmark(workers)
        for workers in WORKER_COUNTS
    ]

    save_results(results)
    create_charts(results)

    baseline = results[0]["mean"]

    print("\nRESULTS")
    print("=" * 60)

    for r in results:
        speedup = baseline / r["mean"]

        print(f"\nWorkers: {r['workers']}")
        print(f"Mean:         {r['mean']:.5f} s")
        print(f"Median:       {r['median']:.5f} s")
        print(f"Std. dev.:    {r['stdev']:.5f} s")
        print(f"Median/mean:  {r['median_mean']:.3f}")
        print(f"Stdev/mean:   {r['stdev_mean']:.3f}")
        print(f"Speed-up:     {speedup:.2f}x")

    print("\nBenchmark completed.")
    print("CSV results and two charts saved.")


if __name__ == "__main__":
    main()
