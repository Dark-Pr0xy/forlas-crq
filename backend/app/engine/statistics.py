"""Display-ready post-processing of the raw loss vector.

Mirrors the Alpha's histogram + LEC build logic so the UI gets the same
shape of payload regardless of which engine produced it.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def percentiles(sorted_losses: np.ndarray) -> dict[str, float]:
    """All the percentiles the dashboard needs, in one pass."""
    if sorted_losses.size == 0:
        return {k: 0.0 for k in ("p5", "p25", "p50", "p75", "p90", "p95", "p99")}
    q = np.array([0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    idx = np.clip((q * sorted_losses.size).astype(np.int64), 0, sorted_losses.size - 1)
    vals = sorted_losses[idx]
    return {
        "p5": float(vals[0]),
        "p25": float(vals[1]),
        "p50": float(vals[2]),
        "p75": float(vals[3]),
        "p90": float(vals[4]),
        "p95": float(vals[5]),
        "p99": float(vals[6]),
    }


def tail_mean(sorted_losses: np.ndarray, q: float = 0.95) -> float:
    """Mean of the worst (1 - q) fraction of iterations."""
    if sorted_losses.size == 0:
        return 0.0
    start = int(np.floor(sorted_losses.size * q))
    tail = sorted_losses[start:]
    return float(tail.mean()) if tail.size else 0.0


def confidence_interval(mean: float, std: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return mean, mean
    half = z * std / np.sqrt(n)
    return mean - half, mean + half


def display_histogram(sorted_losses: np.ndarray, zero_count: int, bins: int = 50) -> dict[str, Any]:
    """Build the display histogram exactly as the Alpha does.

    - Drops zero-loss iterations.
    - Bins range from min non-zero to P99 of non-zero.
    - The right edge collapses everything above P99 into a `tailCount`.
    """
    total = int(sorted_losses.size)
    if zero_count >= total:
        return {
            "lo": 0.0,
            "hi": 1.0,
            "w": 1.0,
            "counts": [0] * bins,
            "cap": 0.0,
            "real_max": 0.0,
            "tail_count": 0,
            "tail_mean": 0.0,
        }
    nz = sorted_losses[zero_count:]
    p99_idx = min(nz.size - 1, int(np.floor(nz.size * 0.99)))
    p99 = float(nz[p99_idx])
    real_max = float(nz[-1])
    lo = float(nz[0])
    cap = p99 if p99 > 0 else real_max
    w = (cap - lo) / bins if (cap - lo) > 0 else 1.0

    # Boolean mask for in-range vs tail
    in_range = nz <= cap
    in_range_vals = nz[in_range]
    tail_vals = nz[~in_range]
    if w == 0:
        counts = [int(in_range_vals.size)] + [0] * (bins - 1)
    else:
        idx = np.clip(((in_range_vals - lo) / w).astype(np.int64), 0, bins - 1)
        counts = np.bincount(idx, minlength=bins).tolist()

    return {
        "lo": lo,
        "hi": cap,
        "w": w,
        "counts": [int(c) for c in counts],
        "cap": cap,
        "real_max": real_max,
        "tail_count": int(tail_vals.size),
        "tail_mean": float(tail_vals.mean()) if tail_vals.size else 0.0,
    }


def lec_curve(
    sorted_losses: np.ndarray, zero_count: int, target_points: int = 800
) -> list[list[float]]:
    """Empirical Loss Exceedance Curve as (loss, P(L > loss)) pairs.

    Matches the Alpha's direct-from-empirical implementation — no anchor-point
    interpolation, so no kinks.
    """
    total = int(sorted_losses.size)
    if total == 0 or zero_count >= total:
        return []
    span = total - zero_count
    step = max(1, span // target_points)
    out: list[list[float]] = []
    out.append([float(sorted_losses[zero_count]), (total - zero_count) / total])
    for i in range(zero_count + step, total, step):
        out.append([float(sorted_losses[i]), (total - i) / total])
    last_x = out[-1][0]
    if last_x != float(sorted_losses[-1]):
        out.append([float(sorted_losses[-1]), 1.0 / total])
    return out
