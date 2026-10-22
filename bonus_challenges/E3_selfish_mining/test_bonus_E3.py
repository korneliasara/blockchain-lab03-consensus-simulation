
import pytest

from bonus_E3_selfish_mining import (
    theoretical_revenue,
    profitability_threshold,
    simulate,
)


@pytest.mark.parametrize(
    "gamma, expected",
    [
        (0.0, 1 / 3),
        (0.5, 1 / 4),
    ],
)
def test_profitability_threshold(gamma, expected):
    assert profitability_threshold(gamma) == pytest.approx(expected)


@pytest.mark.parametrize("gamma", [0.0, 0.5])
def test_theoretical_profitability_boundary(gamma):
    threshold = profitability_threshold(gamma)

    below = threshold - 0.01
    above = threshold + 0.01

    assert theoretical_revenue(below, gamma) < below
    assert theoretical_revenue(above, gamma) > above


@pytest.mark.parametrize(
    "alpha, gamma",
    [
        (0.20, 0.0),
        (0.30, 0.0),
        (0.40, 0.0),
        (0.20, 0.5),
        (0.30, 0.5),
        (0.40, 0.5),
    ],
)
def test_simulation_matches_theory(alpha, gamma):
    actual = simulate(alpha, gamma, events=200_000, seed=42)
    expected = theoretical_revenue(alpha, gamma)

    assert actual == pytest.approx(expected, abs=0.02)


def test_invalid_parameters():
    with pytest.raises(ValueError):
        simulate(-0.1, 0.5)

    with pytest.raises(ValueError):
        simulate(0.3, 1.5)
