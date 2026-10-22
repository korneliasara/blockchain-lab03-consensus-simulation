
import csv
import matplotlib.pyplot as plt


def read_values(filename, column):
    with open(filename, encoding="utf-8") as f:
        rows = csv.DictReader(f)
        return [float(row[column]) for row in rows]


intervals = read_values(
    "partA_intervals.csv", "interval_seconds"
)

difficulties = read_values(
    "partA_difficulty.csv", "difficulty"
)

# Chart 1: Block interval distribution
plt.figure(figsize=(9, 5))
plt.hist(intervals, bins=15, edgecolor="black")
plt.xlabel("Mining time (seconds)")
plt.ylabel("Number of blocks")
plt.title("Proof of Work - Distribution of 100 Block Intervals")
plt.tight_layout()
plt.savefig("partA_interval_histogram.png", dpi=200)
plt.close()

# Chart 2: Difficulty adjustment
plt.figure(figsize=(9, 5))
plt.plot(range(len(difficulties)), difficulties)
plt.xlabel("Block number")
plt.ylabel("Difficulty")
plt.title("Proof of Work - Difficulty Adjustment")
plt.tight_layout()
plt.savefig("partA_difficulty_plot.png", dpi=200)
plt.close()

print("Both charts saved successfully!")
