"""Spearman rank correlation between simulation drivers and total loss."""

from __future__ import annotations

import numpy as np
from scipy import stats


def rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman correlation. Returns 0 for degenerate inputs."""
    if x.size < 2 or y.size < 2:
        return 0.0
    n = min(x.size, y.size)
    if n < 2:
        return 0.0
    res = stats.spearmanr(x[:n], y[:n])
    coef = float(res.statistic if hasattr(res, "statistic") else res.correlation)
    return 0.0 if np.isnan(coef) else coef
