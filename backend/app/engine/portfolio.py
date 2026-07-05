"""Portfolio aggregation.

For SMB use cases (a few dozen scenarios at ~100K iterations) we treat
scenarios as independent and sum loss vectors element-wise. This is exact for
the independent case — the resulting sample is one observation of the
portfolio's annual loss — and gives correct percentiles via the empirical
distribution of the sum.

If the scenarios were simulated at different iteration counts, we resize each
vector to the minimum common length (a simple truncation of the longer
samples; we use the deterministic seed at the head of each vector).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.engine.statistics import (
    confidence_interval,
    display_histogram,
    lec_curve,
    percentiles,
    tail_mean,
)


@dataclass
class PortfolioInput:
    scenario_public_id: str
    scenario_name: str
    tolerance: float
    losses: np.ndarray  # shape (n_iter,)


@dataclass
class PortfolioRollupResult:
    iterations: int
    scenario_count: int
    total_ale: float
    total_p50: float
    total_p90: float
    total_p95: float
    total_p99: float
    total_tail: float
    ci_lo: float
    ci_hi: float
    over_tolerance_count: int
    portfolio_losses: np.ndarray
    histogram: dict[str, Any]
    lec_curve: list[list[float]]
    per_scenario: list[dict[str, Any]]


def aggregate(
    inputs: list[PortfolioInput],
    *,
    insurance_deductible: float = 0.0,
    insurance_limit: float | None = None,
) -> PortfolioRollupResult:
    """Aggregate independent scenario loss vectors into a portfolio rollup.

    `insurance_*` parameters apply an additive offset PER YEAR after summing,
    bounded by the policy limit. The recovery is `min(limit, max(0, loss -
    deductible))`.

    Per-scenario percentiles use the same empirical floor-index method as the
    engine's headline stats (`engine.statistics.percentiles`) so the Dashboard
    top-drivers table matches the Workspace P95/P99 for the same run (M3).
    """
    if not inputs:
        return _empty_result()

    n_iter = min(int(arr.losses.size) for arr in inputs)
    if n_iter == 0:
        return _empty_result()

    # Element-wise sum of (truncated) loss vectors
    summed = np.zeros(n_iter, dtype=np.float64)
    per_scenario: list[dict[str, Any]] = []
    over_tolerance = 0
    for entry in inputs:
        slice_ = entry.losses[:n_iter]
        summed += slice_
        mean = float(slice_.mean())
        scn_pcts = percentiles(np.sort(slice_))
        p95 = scn_pcts["p95"]
        p99 = scn_pcts["p99"]
        is_over = entry.tolerance > 0 and mean > entry.tolerance
        if is_over:
            over_tolerance += 1
        per_scenario.append(
            {
                "scenario_id": entry.scenario_public_id,
                "name": entry.scenario_name,
                "ale": mean,
                "p95": p95,
                "p99": p99,
                "tolerance": entry.tolerance,
                "utilisation": (mean / entry.tolerance) if entry.tolerance > 0 else 0.0,
                "over_tolerance": is_over,
                "share_of_ale": 0.0,  # populated after totals computed
            }
        )

    # Insurance offset (applies to the aggregate, not per-scenario)
    if insurance_limit is not None or insurance_deductible > 0:
        limit = insurance_limit if insurance_limit is not None else float("inf")
        recovery = np.clip(summed - insurance_deductible, 0.0, limit)
        summed = np.maximum(0.0, summed - recovery)

    sorted_losses = np.sort(summed)
    mean = float(summed.mean())
    std = float(summed.std(ddof=0))
    pcts = percentiles(sorted_losses)
    ci_lo, ci_hi = confidence_interval(mean, std, n_iter)
    tail = tail_mean(sorted_losses, 0.95)
    zero_count = int(np.searchsorted(sorted_losses, 0, side="right"))
    hist = display_histogram(sorted_losses, zero_count, 50)
    lec = lec_curve(sorted_losses, zero_count, 600)

    if mean > 0:
        for entry in per_scenario:
            entry["share_of_ale"] = entry["ale"] / mean if mean else 0.0
    per_scenario.sort(key=lambda d: d["ale"], reverse=True)

    return PortfolioRollupResult(
        iterations=n_iter,
        scenario_count=len(inputs),
        total_ale=mean,
        total_p50=pcts["p50"],
        total_p90=pcts["p90"],
        total_p95=pcts["p95"],
        total_p99=pcts["p99"],
        total_tail=tail,
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        over_tolerance_count=over_tolerance,
        portfolio_losses=summed,
        histogram=hist,
        lec_curve=lec,
        per_scenario=per_scenario,
    )


def _empty_result() -> PortfolioRollupResult:
    return PortfolioRollupResult(
        iterations=0,
        scenario_count=0,
        total_ale=0.0,
        total_p50=0.0,
        total_p90=0.0,
        total_p95=0.0,
        total_p99=0.0,
        total_tail=0.0,
        ci_lo=0.0,
        ci_hi=0.0,
        over_tolerance_count=0,
        portfolio_losses=np.zeros(0),
        histogram={
            "lo": 0.0,
            "hi": 1.0,
            "w": 1.0,
            "counts": [0] * 50,
            "cap": 0.0,
            "real_max": 0.0,
            "tail_count": 0,
            "tail_mean": 0.0,
        },
        lec_curve=[],
        per_scenario=[],
    )
