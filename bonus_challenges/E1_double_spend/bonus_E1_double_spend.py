
"""Lab 03 Bonus E1 - Bitcoin double-spend probability."""

import math
import random
import csv


def attacker_success(q: float, z: int) -> float:
    """Bitcoin whitepaper Section 11 probability."""

    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")

    if z < 0:
        raise ValueError("z cannot be negative")

    if z == 0 or q >= 0.5:
        return 1.0

    p = 1.0 - q
    lam = z * q / p

    probability = 1.0
    poisson = math.exp(-lam)

    for k in range(z + 1):
        catch_up = (q / p) ** (z - k)
        probability -= poisson * (1 - catch_up)

        if k < z:
            poisson *= lam / (k + 1)

    return max(0.0, min(1.0, probability))


def poisson_sample(lam: float, rng: random.Random) -> int:
    """Sample a Poisson random variable."""
    limit = math.exp(-lam)
    product = 1.0
    count = 0

    while product > limit:
        product *= rng.random()
        count += 1

    return count - 1


def monte_carlo(q: float, z: int, trials: int = 1_000_000,
                seed: int = 42):
    """Simulate the whitepaper's Poisson catch-up model."""
    rng = random.Random(seed)
    p = 1.0 - q
    lam = z * q / p
    successes = 0

    for _ in range(trials):
        k = poisson_sample(lam, rng)

        if k >= z:
            successes += 1
        else:
            # Probability of eventually catching up
            probability = (q / p) ** (z - k)
            if rng.random() < probability:
                successes += 1

    estimate = successes / trials
    standard_error = math.sqrt(
        estimate * (1 - estimate) / trials
    )

    return estimate, standard_error


def confirmation_threshold(q: float, target: float) -> int:
    """Minimum confirmations for success probability below target."""
    for z in range(1, 1001):
        if attacker_success(q, z) < target:
            return z

    raise ValueError("Threshold not reached")



def main():
    cases = [
        (0.10, 5, 0.0009137),
        (0.10, 6, 0.0002428),
        (0.30, 5, 0.1773523),
    ]

    print("BONUS E1 - DOUBLE-SPEND PROBABILITY")
    print("=" * 72)
    print("Whitepaper reference values")

    for q, z, expected in cases:
        actual = attacker_success(q, z)
        print(
            f"q={q:.2f}, z={z}: "
            f"Calculated={actual:.7f}, "
            f"Expected={expected:.7f}"
        )
        assert abs(actual - expected) < 0.000001

    print("\nMONTE CARLO COMPARISON")
    print("=" * 72)

    for q, z, _ in cases:
        analytical = attacker_success(q, z)
        trials = 5_000_000 if (q == 0.10 and z == 6) else 1_000_000
        estimate, se = monte_carlo(q, z, trials=trials)
        relative_error = (
            abs(estimate - analytical) / analytical * 100
        )

        print(f"\nq={q:.2f}, z={z}")
        print(f"Analytical probability: {analytical:.7f}")
        print(f"Monte Carlo estimate:  {estimate:.7f}")
        print(f"Relative error:        {relative_error:.2f}%")
        print(f"95% margin approx.:   {1.96 * se:.7f}")

    print("\nCONFIRMATION THRESHOLDS")
    print("=" * 72)

    with open(
        "bonus_E1_thresholds.csv", "w",
        newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "attacker_share",
            "below_10_percent",
            "below_1_percent",
            "below_0_1_percent",
        ])

        for q in [0.10, 0.30, 0.45]:
            thresholds = [
                confirmation_threshold(q, target)
                for target in [0.10, 0.01, 0.001]
            ]

            writer.writerow([q, *thresholds])

            print(
                f"q={q:.2f}: "
                f"10% -> z={thresholds[0]}, "
                f"1% -> z={thresholds[1]}, "
                f"0.1% -> z={thresholds[2]}"
            )

    print("\nBonus E1 calculations completed.")
    print("Thresholds saved to bonus_E1_thresholds.csv")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
