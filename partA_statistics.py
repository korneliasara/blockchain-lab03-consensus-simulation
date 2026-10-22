
import csv

from consensus.pow import simulate_mining


def save_csv(filename, header, rows):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    print("PART A - PROOF OF WORK STATISTICS")
    print("=" * 45)

    chain, stats = simulate_mining(
        blocks=100,
        workers=1,
        target_seconds=1.0,
    )

    print(stats.report(1.0))

    save_csv(
        "partA_intervals.csv",
        ["block", "interval_seconds"],
        enumerate(stats.intervals, start=1),
    )

    save_csv(
        "partA_difficulty.csv",
        ["block", "difficulty"],
        enumerate(stats.difficulties),
    )

    print("\nResults saved successfully.")
    print("partA_intervals.csv")
    print("partA_difficulty.csv")


if __name__ == "__main__":
    main()
