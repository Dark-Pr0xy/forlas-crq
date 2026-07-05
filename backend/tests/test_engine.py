"""Engine-level tests — distributions, statistics, simulation invariants."""

from __future__ import annotations

import numpy as np
import pytest

from app.engine import run_simulation
from app.engine.distributions import sample
from app.engine.rng import default_rng
from app.engine.simulation import RunOptions
from app.engine.statistics import (
    confidence_interval,
    display_histogram,
    lec_curve,
    percentiles,
    tail_mean,
)


@pytest.fixture
def rng():
    return default_rng(42)


# ---------------------------------------------------------------- distributions


def test_pert_respects_bounds(rng):
    samples = sample(rng, 20_000, {"type": "pert", "min": 10, "mode": 30, "max": 50})
    assert samples.min() >= 10
    assert samples.max() <= 50
    # PERT with mode=30 over [10, 50] has mean ≈ (10 + 4*30 + 50) / 6 = 30
    assert abs(samples.mean() - 30) < 0.5


def test_triangular_respects_bounds(rng):
    samples = sample(rng, 20_000, {"type": "triangular", "min": 0, "mode": 5, "max": 10})
    assert samples.min() >= 0
    assert samples.max() <= 10
    # Mean of triangular(a, m, b) = (a + m + b) / 3 = 5
    assert abs(samples.mean() - 5) < 0.1


def test_uniform_shape(rng):
    samples = sample(rng, 10_000, {"type": "uniform", "min": -3, "max": 7})
    assert -3 <= samples.min()
    assert samples.max() <= 7
    assert abs(samples.mean() - 2) < 0.1


def test_lognormal_p10_p90_fit(rng):
    samples = sample(rng, 200_000, {"type": "lognormal", "min": 10_000, "max": 1_000_000})
    p10 = np.percentile(samples, 10)
    p90 = np.percentile(samples, 90)
    # Within ±5% of declared anchors
    assert abs(p10 - 10_000) / 10_000 < 0.05
    assert abs(p90 - 1_000_000) / 1_000_000 < 0.05


def test_beta_bounds(rng):
    samples = sample(rng, 10_000, {"type": "beta", "min": 0, "max": 1, "alpha": 2, "beta": 5})
    assert 0 <= samples.min()
    assert samples.max() <= 1
    # E[Beta(2, 5)] = 2 / 7 ≈ 0.286
    assert abs(samples.mean() - 2 / 7) < 0.02


def test_gamma_nonneg(rng):
    samples = sample(rng, 10_000, {"type": "gamma", "min": 0, "max": 100, "shape": 2})
    assert samples.min() >= 0


def test_lognormal_zero_returns_zeros(rng):
    # Modelling "no secondary loss": both anchors at 0 → all zeros, not floored
    # up to 1 (UAT #2).
    samples = sample(rng, 5_000, {"type": "lognormal", "min": 0, "max": 0})
    assert samples.max() == 0.0
    assert samples.min() == 0.0


def test_zero_secondary_loss_produces_no_secondary(rng):
    from app.engine import run_simulation
    from app.engine.simulation import RunOptions

    scenario = {
        "mode": "tef-vuln",
        "tolerance": 0,
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 4, "max": 10},
            "vuln": {"type": "pert", "min": 0.1, "mode": 0.3, "max": 0.5},
            "plm": {"type": "pert", "min": 100_000, "mode": 200_000, "max": 300_000},
            "slp_prob": {"type": "pert", "min": 0, "mode": 0, "max": 0},
            "slm": {"type": "lognormal", "min": 0, "max": 0},
        },
    }
    result = run_simulation(scenario, RunOptions(iterations=5_000, seed=1))
    # Runs cleanly and produces positive primary-only losses.
    assert result.mean > 0


# ---------------------------------------------------------------- statistics


def test_percentiles_monotone():
    arr = np.sort(np.linspace(0, 1000, 10_000))
    p = percentiles(arr)
    assert p["p5"] < p["p50"] < p["p95"] < p["p99"]


def test_confidence_interval_widens_with_variance():
    lo1, hi1 = confidence_interval(100, 10, 1000)
    lo2, hi2 = confidence_interval(100, 50, 1000)
    assert (hi2 - lo2) > (hi1 - lo1)


def test_tail_mean_above_p95():
    arr = np.sort(np.random.default_rng(1).pareto(2, 50_000) * 1000)
    p95 = float(arr[int(0.95 * arr.size)])
    assert tail_mean(arr, 0.95) >= p95


def test_histogram_handles_all_zeros():
    arr = np.zeros(1000)
    hist = display_histogram(arr, 1000, 50)
    assert sum(hist["counts"]) == 0
    assert hist["tail_count"] == 0


def test_lec_curve_descending():
    arr = np.sort(np.array([0, 0, 100, 200, 300, 400, 500, 1000], dtype=float))
    pts = lec_curve(arr, zero_count=2, target_points=10)
    losses = [p[0] for p in pts]
    probs = [p[1] for p in pts]
    assert losses == sorted(losses)
    assert all(probs[i] >= probs[i + 1] for i in range(len(probs) - 1))
    assert probs[0] <= 1.0


# ---------------------------------------------------------------- simulation


@pytest.fixture
def ransomware_scenario():
    return {
        "mode": "tef-vuln",
        "tolerance": 5_000_000,
        "reduction_pct": 0,
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 4, "max": 12},
            "vuln": {"type": "pert", "min": 0.05, "mode": 0.25, "max": 0.6},
            "plm": {"type": "lognormal", "min": 200_000, "max": 6_000_000},
            "slp_prob": {"type": "pert", "min": 0.3, "mode": 0.55, "max": 0.85},
            "slm": {"type": "lognormal", "min": 100_000, "max": 8_000_000},
        },
    }


def test_simulation_tef_vuln_mode(ransomware_scenario):
    result = run_simulation(ransomware_scenario, RunOptions(iterations=50_000, seed=42))
    assert result.iterations == 50_000
    assert result.mean > 0
    assert result.p50 <= result.p95 <= result.p99
    assert result.ci_lo <= result.mean <= result.ci_hi
    assert result.zero_count >= 0
    assert result.tail_mean >= result.p95
    assert result.prob_exceed_tolerance >= 0
    assert len(result.lec_curve) > 0
    assert result.histogram["cap"] > 0
    assert any(d["name"] == "tef" for d in result.sensitivity)


def test_simulation_lef_mode():
    scenario = {
        "mode": "lef",
        "tolerance": 1_000_000,
        "reduction_pct": 0,
        "inputs": {
            "lef": {"type": "pert", "min": 0.5, "mode": 2, "max": 6},
            "plm": {"type": "pert", "min": 50_000, "mode": 250_000, "max": 1_500_000},
            "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
            "slm": {"type": "pert", "min": 25_000, "mode": 150_000, "max": 2_000_000},
        },
    }
    result = run_simulation(scenario, RunOptions(iterations=20_000, seed=42))
    assert result.mean > 0
    assert result.mode == "lef"
    assert any(d["name"] == "lef" for d in result.sensitivity)


def test_simulation_full_decomposition_mode():
    scenario = {
        "mode": "full",
        "tolerance": 2_000_000,
        "reduction_pct": 0,
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 6, "max": 24},
            "tcap": {"type": "pert", "min": 30, "mode": 55, "max": 85},
            "rs": {"type": "pert", "min": 40, "mode": 65, "max": 90},
            "plm": {"type": "lognormal", "min": 50_000, "max": 1_500_000},
            "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
            "slm": {"type": "lognormal", "min": 25_000, "max": 2_000_000},
        },
    }
    result = run_simulation(scenario, RunOptions(iterations=20_000, seed=42))
    assert result.mean > 0
    assert any(d["name"] == "tef" for d in result.sensitivity)
    assert any(d["name"] == "vuln" for d in result.sensitivity)


def test_simulation_deterministic_at_fixed_seed(ransomware_scenario):
    r1 = run_simulation(ransomware_scenario, RunOptions(iterations=10_000, seed=99))
    r2 = run_simulation(ransomware_scenario, RunOptions(iterations=10_000, seed=99))
    assert r1.mean == r2.mean
    assert r1.p95 == r2.p95
    np.testing.assert_array_equal(r1.sorted_losses, r2.sorted_losses)


def test_simulation_reduction_lowers_losses(ransomware_scenario):
    baseline = run_simulation(ransomware_scenario, RunOptions(iterations=10_000, seed=7))
    reduced = dict(ransomware_scenario)
    reduced["reduction_pct"] = 40
    after = run_simulation(reduced, RunOptions(iterations=10_000, seed=7))
    assert after.mean < baseline.mean
    # Reduction is proportional — within 0.5% of analytical expectation
    assert abs(after.mean - baseline.mean * 0.6) / baseline.mean < 0.005
