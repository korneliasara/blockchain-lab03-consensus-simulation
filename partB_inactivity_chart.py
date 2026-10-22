
import csv
import matplotlib.pyplot as plt

epochs = []
shares = []

with open(
    "partB_inactivity_results.csv",
    encoding="utf-8",
) as file:
    for row in csv.DictReader(file):
        epochs.append(int(row["epoch"]))
        shares.append(float(row["voting_share_percent"]))

plt.figure(figsize=(9, 5))

plt.plot(epochs, shares, linewidth=2)

plt.axhline(
    100 * 2 / 3,
    linestyle="--",
    label="Two-thirds threshold",
)

plt.xlabel("Epoch")
plt.ylabel("Participating stake (%)")
plt.title("Casper FFG - Inactivity Leak and Finality Recovery")
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("partB_inactivity_plot.png", dpi=200)
plt.close()

print("Inactivity leak chart saved successfully!")
