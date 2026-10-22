
import csv
import matplotlib.pyplot as plt

offenders = []
losses = []

with open(
    "partB_slashing_results.csv",
    encoding="utf-8",
) as file:
    reader = csv.DictReader(file)

    for row in reader:
        offenders.append(int(row["offenders"]))
        losses.append(float(row["loss_eth"]))

plt.figure(figsize=(9, 5))

plt.plot(offenders, losses, marker="o", linewidth=2)

plt.axhline(
    y=32,
    linestyle="--",
    label="Maximum stake: 32 ETH",
)

plt.xlabel("Number of simultaneous offenders")
plt.ylabel("Loss per validator (ETH)")
plt.title("Casper FFG - Correlated Slashing Penalties")

plt.xticks(offenders)
plt.ylim(0, 35)
plt.grid(alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("partB_slashing_plot.png", dpi=200)
plt.close()

print("Slashing chart saved successfully!")
