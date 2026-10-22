
import matplotlib.pyplot as plt
from bonus_E1_double_spend import attacker_success

confirmations = list(range(1, 401))

plt.figure(figsize=(10, 6))

for q in [0.10, 0.30, 0.45]:
    probabilities = [
        attacker_success(q, z)
        for z in confirmations
    ]
    plt.plot(
        confirmations,
        probabilities,
        label=f"Attacker hash share: {q:.0%}",
    )

for threshold in [0.10, 0.01, 0.001]:
    plt.axhline(
        threshold,
        linestyle="--",
        alpha=0.5,
    )

plt.yscale("log")
plt.xlabel("Number of confirmations (z)")
plt.ylabel("Attacker success probability")
plt.title("Bitcoin Double-Spend Probability")
plt.ylim(0.00001, 1)
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("bonus_E1_probability_plot.png", dpi=200)
plt.close()

print("Bonus E1 chart saved successfully!")
