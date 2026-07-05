"""Monte Carlo simulation — vectorised NumPy port of the Alpha's runSimulation.

Implements all three decomposition modes:

    - 'lef'      Loss-event frequency sampled directly.
    - 'tef-vuln' Threat-event frequency multiplied by a vulnerability probability.
    - 'full'     Vulnerability decomposed into Threat Capability vs Resistance
                 Strength via a logistic function (Alpha behaviour).

Output shape mirrors the Alpha's `runSimulation` return, augmented with
fields that the Beta surfaces and the Alpha did not (engine_version, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from app.engine import distributions as dist
from app.engine.errors import validate_inputs
from app.engine.rng import default_rng
from app.engine.sensitivity import rank_corr
from app.engine.statistics import (
    confidence_interval,
    display_histogram,
    lec_curve,
    percentiles,
    tail_mean,
)

ENGINE_VERSION = "1.0.0-numpy"


@dataclass
class RunOptions:
    iterations: int = 100_000
    seed: int = 42


@dataclass
class RunResult:
    iterations: int
    seed: int
    mean: float
    std: float
    p5: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    ci_lo: float
    ci_hi: float
    tail_mean: float
    zero_count: int
    total_count: int
    prob_exceed_tolerance: float
    tolerance: float
    tolerance_utilisation: float
    difference_to_tolerance: float
    losses: np.ndarray
    sorted_losses: np.ndarray
    lefs: np.ndarray
    histogram: dict[str, Any]
    lec_curve: list[list[float]]
    sensitivity: list[dict[str, Any]]
    driver_samples: dict[str, list[float]]
    mode: str
    engine_version: str = ENGINE_VERSION
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _draw_lef(
    rng: np.random.Generator, n: int, mode: str, inputs: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lef, tef, vuln) arrays of shape (n,) given the chosen mode.

    For mode='lef', `tef` and `vuln` are zeros (kept for shape consistency).
    """
    if mode == "lef":
        lef = np.maximum(0, dist.sample(rng, n, inputs["lef"]))
        zeros = np.zeros(n)
        return lef, zeros, zeros

    tef = np.maximum(0, dist.sample(rng, n, inputs["tef"]))

    if mode == "tef-vuln":
        vuln = np.clip(dist.sample(rng, n, inputs["vuln"]), 0.0, 1.0)
        return tef * vuln, tef, vuln

    # mode == 'full' — derive vuln from threat capability vs resistance strength
    tcap = dist.sample(rng, n, inputs["tcap"])
    rs = dist.sample(rng, n, inputs["rs"])
    rs_params = inputs["rs"]
    spread = max(
        1.0,
        (float(rs_params.get("max", 100)) - float(rs_params.get("min", 0))) / 8.0,
    )
    vuln = 1.0 / (1.0 + np.exp(-(tcap - rs) / spread))
    return tef * vuln, tef, vuln


def _segmented_sum(values: np.ndarray, counts: np.ndarray) -> np.ndarray:
    """Faster alternative to a Python loop for per-iteration sums."""
    if values.size == 0:
        return np.zeros(counts.size)
    starts = np.zeros(counts.size + 1, dtype=np.int64)
    np.cumsum(counts, out=starts[1:])
    out = np.zeros(counts.size)
    # np.add.reduceat handles segments; skip empty segments
    non_empty = counts > 0
    if not non_empty.any():
        return out
    seg_starts = starts[:-1][non_empty]
    summed = np.add.reduceat(values, seg_starts)
    out[non_empty] = summed
    return out


def run_simulation(
    scenario: dict[str, Any], opts: RunOptions | None = None
) -> RunResult:
    """Execute the FAIR Monte Carlo for a single scenario.

    `scenario` must contain `mode` and `inputs`; `tolerance` and `reduction_pct`
    are optional.
    """
    opts = opts or RunOptions()
    iters = int(opts.iterations)
    seed = int(opts.seed)
    rng = default_rng(seed)
    mode = scenario.get("mode", "tef-vuln")
    inputs = scenario["inputs"]
    # Fail fast with a clear, caller-fixable message before we touch the RNG.
    validate_inputs(mode, inputs)
    tolerance = float(scenario.get("tolerance", 0.0) or 0.0)
    reduction_pct = float(scenario.get("reduction_pct", 0.0) or 0.0)
    reduction_factor = max(0.0, 1.0 - reduction_pct / 100.0)

    # Driver samples — LEF, TEF, vuln (per mode), then per-event aggregates
    lef, tef, vuln = _draw_lef(rng, iters, mode, inputs)
    n_events = rng.poisson(lef).astype(np.int64)

    # Event sampling — vectorised with cumulative segment sums
    total_events = int(n_events.sum())
    if total_events:
        prim_flat = np.maximum(0, dist.sample(rng, total_events, inputs["plm"]))
        sprob_flat = np.clip(dist.sample(rng, total_events, inputs["slp_prob"]), 0.0, 1.0)
        sec_flat = np.maximum(0, dist.sample(rng, total_events, inputs["slm"]))
        sec_triggered = rng.uniform(0, 1, total_events) < sprob_flat
        sec_loss_flat = np.where(sec_triggered, sec_flat, 0.0)
        event_loss_flat = prim_flat + sec_loss_flat
        losses = _segmented_sum(event_loss_flat, n_events)
        primary_per_iter = _segmented_sum(prim_flat, n_events)
        secondary_per_iter = _segmented_sum(sec_loss_flat, n_events)
    else:
        losses = np.zeros(iters)
        primary_per_iter = np.zeros(iters)
        secondary_per_iter = np.zeros(iters)

    losses *= reduction_factor

    sorted_losses = np.sort(losses)
    mean = float(losses.mean())
    std = float(losses.std(ddof=0))
    pcts = percentiles(sorted_losses)
    ci_lo, ci_hi = confidence_interval(mean, std, iters)
    tail = tail_mean(sorted_losses, 0.95)
    zero_count = int(np.searchsorted(sorted_losses, 0, side="right"))
    hist = display_histogram(sorted_losses, zero_count, 50)
    lec = lec_curve(sorted_losses, zero_count, 800)

    prob_exceed = (
        float((sorted_losses > tolerance).sum() / iters) if tolerance > 0 else 0.0
    )
    tolerance_util = mean / tolerance if tolerance > 0 else 0.0
    diff_to_tol = tolerance - mean

    # Sensitivity — match the Alpha's driver set per mode
    if mode == "lef":
        driver_arrays = {"lef": lef, "primary": primary_per_iter, "secondary": secondary_per_iter}
        driver_labels = {
            "lef": "Loss Event Frequency",
            "primary": "Primary Loss Magnitude",
            "secondary": "Secondary Loss",
        }
    else:
        driver_arrays = {
            "tef": tef,
            "vuln": vuln,
            "primary": primary_per_iter,
            "secondary": secondary_per_iter,
        }
        driver_labels = {
            "tef": "Threat Event Frequency",
            "vuln": "Vulnerability" if mode == "tef-vuln" else "Vulnerability (derived)",
            "primary": "Primary Loss Magnitude",
            "secondary": "Secondary Loss",
        }

    sensitivity = []
    for name, arr in driver_arrays.items():
        sensitivity.append(
            {
                "name": name,
                "label": driver_labels[name],
                "corr": rank_corr(arr, losses),
            }
        )
    sensitivity.sort(key=lambda d: abs(d["corr"]), reverse=True)

    sample_every = max(1, iters // 2000)
    driver_samples = {
        k: arr[::sample_every].astype(float).tolist() for k, arr in driver_arrays.items()
    }

    return RunResult(
        iterations=iters,
        seed=seed,
        mean=mean,
        std=std,
        p5=pcts["p5"],
        p25=pcts["p25"],
        p50=pcts["p50"],
        p75=pcts["p75"],
        p90=pcts["p90"],
        p95=pcts["p95"],
        p99=pcts["p99"],
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        tail_mean=tail,
        zero_count=zero_count,
        total_count=iters,
        prob_exceed_tolerance=prob_exceed,
        tolerance=tolerance,
        tolerance_utilisation=tolerance_util,
        difference_to_tolerance=diff_to_tol,
        losses=losses,
        sorted_losses=sorted_losses,
        lefs=lef,
        histogram=hist,
        lec_curve=lec,
        sensitivity=sensitivity,
        driver_samples=driver_samples,
        mode=mode,
    )
