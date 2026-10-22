
"""Bonus E3 - Eyal-Sirer selfish mining event simulation."""

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt


def theoretical_revenue(alpha, gamma):
    """Eyal-Sirer selfish pool relative revenue."""
    if not 0 <= alpha < 0.5:
        raise ValueError("alpha must be in [0, 0.5)")
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1]")

    numerator = (
        alpha * (1 - alpha) ** 2
        * (4 * alpha + gamma * (1 - 2 * alpha))
        - alpha ** 3
    )
    denominator = (
        1 - alpha * (1 + (2 - alpha) * alpha)
    )
    return numerator / denominator


def profitability_threshold(gamma):
    return (1 - gamma) / (3 - 2 * gamma)


def simulate(alpha, gamma, events=250_000, seed=42):
    """Event-based Eyal-Sirer selfish mining strategy."""

    if not 0 <= alpha < 0.5:
        raise ValueError("alpha must be in [0, 0.5)")
    if not 0 <= gamma <= 1:
        raise ValueError("gamma must be in [0, 1]")

    rng = random.Random(seed)

    lead = 0
    selfish_rewards = 0
    honest_rewards = 0

    for _ in range(events):
        attacker_mines = rng.random() < alpha

        # State -1 represents a public tie (0').
        if lead == -1:
            if attacker_mines:
                selfish_rewards += 2
            elif rng.random() < gamma:
                selfish_rewards += 1
                honest_rewards += 1
            else:
                honest_rewards += 2

            lead = 0

        elif lead == 0:
            if attacker_mines:
                lead = 1
            else:
                honest_rewards += 1

        elif lead == 1:
            if attacker_mines:
                lead = 2
            else:
                # Publish the withheld block and start a race.
                lead = -1

        elif lead == 2:
            if attacker_mines:
                lead = 3
            else:
                # Release the private two-block chain.
                selfish_rewards += 2
                lead = 0

        else:
            if attacker_mines:
                lead += 1
            else:
                # Publish one block to maintain an advantage.
                selfish_rewards += 1
                lead -= 1

    total = selfish_rewards + honest_rewards

    return selfish_rewards / total if total else 0.0


def main():
    output = Path(__file__).resolve().parent
    alphas = [i / 1000 for i in range(50, 491, 10)]
    gamma_values = [0.0, 0.5]

    print("BONUS E3 - SELFISH MINING")
    print("=" * 60)

    rows = []

    for gamma in gamma_values:
        threshold = profitability_threshold(gamma)

        print(f"\nGamma = {gamma}")
        print(f"Expected profitability threshold: {threshold:.4f}")

        for alpha in alphas:
            theory = theoretical_revenue(alpha, gamma)
            simulation = simulate(
                alpha, gamma,
                events=250_000,
                seed=42 + int(alpha * 1000) + int(gamma * 100),
            )

            rows.append([
                alpha, gamma, theory, simulation, alpha
            ])

    with open(
        output / "bonus_E3_results.csv",
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "alpha", "gamma", "theoretical_revenue",
            "simulated_revenue", "honest_revenue"
        ])
        writer.writerows(rows)

    plt.figure(figsize=(10, 6))

    plt.plot(
        alphas, alphas,
        color="black", linestyle="--",
        label="Honest mining: R = alpha"
    )

    colors = {0.0: "tab:blue", 0.5: "tab:orange"}

    for gamma in gamma_values:
        theory = [
            theoretical_revenue(a, gamma)
            for a in alphas
        ]

        simulated = [
            row[3] for row in rows
            if row[1] == gamma
        ]

        plt.plot(
            alphas, theory,
            color=colors[gamma],
            label=f"Selfish mining theory (gamma={gamma})"
        )

        plt.scatter(
            alphas[::3], simulated[::3],
            color=colors[gamma],
            s=16,
            label=f"Simulation (gamma={gamma})"
        )

    plt.axvline(
        1 / 3, color="tab:blue",
        linestyle=":", alpha=0.6
    )
    plt.axvline(
        1 / 4, color="tab:orange",
        linestyle=":", alpha=0.6
    )

    plt.xlabel("Attacker hash share (alpha)")
    plt.ylabel("Fraction of accepted block rewards")
    plt.title("Eyal-Sirer Selfish Mining Profitability")
    plt.legend()
    plt.grid(alpha=0.25)
    plt.tight_layout()

    plt.savefig(
        output / "bonus_E3_revenue_plot.png",
        dpi=200
    )
    plt.close()

    print("\nSample comparison:")
    for gamma in gamma_values:
        for alpha in [0.20, 0.30, 0.40]:
            theory = theoretical_revenue(alpha, gamma)
            simulated = simulate(
                alpha, gamma, events=1_000_000, seed=42
            )

            print(
                f"alpha={alpha:.2f}, gamma={gamma:.1f}: "
                f"honest={alpha:.4f}, "
                f"theory={theory:.4f}, "
                f"simulation={simulated:.4f}"
            )

    print("\nResults and chart saved successfully!")


if __name__ == "__main__":
    main()
