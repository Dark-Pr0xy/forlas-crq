"""Vectorised distribution samplers.

Each function returns an `np.ndarray` of shape `(n,)`. They match the Alpha's
semantics:

    - normal: mean = (min + max) / 2, sd = (max - min) / 6
    - lognormal: fit to 10th / 90th percentiles (Alpha's behaviour)
    - PERT: beta-distributed on [a, b] with shape parameters derived from
      (a, m, b, lambda)
    - beta: alpha, beta on [a, b]
    - gamma: shape * scale, scale = (max - min) / 6 by default

The Alpha's `sample()` switch is collapsed into a `sample()` helper that
dispatches by `type`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

# 10th / 90th percentile z-scores (used to fit a lognormal from observed p10/p90)
Z10 = -1.2815515655
Z90 = 1.2815515655


from app.engine.errors import SimulationInputError


class DistError(SimulationInputError):
    """Raised for malformed distribution parameters.

    Subclasses SimulationInputError so the API maps it to HTTP 422 alongside
    the mode/required-variable checks.
    """


def _get(p: dict[str, Any], *keys: str, default: float | None = None) -> float | None:
    for k in keys:
        v = p.get(k)
        if v is not None:
            return float(v)
    return default


def _uniform(rng: np.random.Generator, n: int, a: float, b: float) -> np.ndarray:
    return rng.uniform(a, b, n)


def _triangular(rng: np.random.Generator, n: int, a: float, m: float, b: float) -> np.ndarray:
    if not (a <= m <= b):
        raise DistError(f"triangular requires a <= m <= b ({a},{m},{b})")
    return rng.triangular(a, m, b, n)


def _pert(
    rng: np.random.Generator, n: int, a: float, m: float, b: float, lam: float = 4.0
) -> np.ndarray:
    if b <= a:
        return np.full(n, a, dtype=np.float64)
    if not (a <= m <= b):
        raise DistError(f"pert requires a <= m <= b ({a},{m},{b})")
    alpha = 1 + lam * (m - a) / (b - a)
    beta = 1 + lam * (b - m) / (b - a)
    return a + rng.beta(alpha, beta, n) * (b - a)


def _normal(rng: np.random.Generator, n: int, a: float, b: float) -> np.ndarray:
    # Alpha derives mean/sd from min/max for parity with its `sample()` dispatch.
    mean = (a + b) / 2.0
    sd = (b - a) / 6.0
    return rng.normal(mean, sd, n)


def _lognormal(rng: np.random.Generator, n: int, p10: float, p90: float) -> np.ndarray:
    # Degenerate case: both anchors at (or below) zero means "no loss here" —
    # e.g. modelling a scenario with no secondary loss. Return zeros rather than
    # flooring up to 1 (lognormal is strictly positive, so this is the only way
    # to express an actual zero).
    if float(p90) <= 0.0:
        return np.zeros(n, dtype=np.float64)
    p10 = max(1.0, float(p10))
    p90 = max(p10 + 1.0, float(p90))
    sigma = (np.log(p90) - np.log(p10)) / (Z90 - Z10)
    mu = np.log(p10) - Z10 * sigma
    return rng.lognormal(mu, sigma, n)


def _beta_dist(
    rng: np.random.Generator, n: int, a: float, b: float, alpha: float, beta: float
) -> np.ndarray:
    return a + rng.beta(alpha, beta, n) * (b - a)


def _gamma(
    rng: np.random.Generator, n: int, shape: float, scale: float, offset: float = 0.0
) -> np.ndarray:
    return offset + rng.gamma(shape, scale, n)


# ----------------------------------------------------------------- public API


def sample(rng: np.random.Generator, n: int, params: dict[str, Any]) -> np.ndarray:
    """Draw `n` samples from the distribution described by `params`.

    `params` matches the persisted JSON shape (`type`, `min`, `mode`, `max`,
    `alpha`, `beta`, `shape`, `lambda`).
    """
    if params is None:
        raise DistError("distribution params missing")
    t = params.get("type", "pert")

    # Plugin-contributed distributions override / extend the built-ins.
    # Imported lazily to avoid a circular import (plugins → engine → plugins).
    from app.plugins import registry as _plugin_registry

    if t in _plugin_registry.distributions:
        return _plugin_registry.distributions[t].sampler(rng, n, params)

    if t == "pert":
        a = _get(params, "min")
        m = _get(params, "mode")
        b = _get(params, "max")
        lam = _get(params, "lambda", "lambda_", default=4.0) or 4.0
        if a is None or m is None or b is None:
            raise DistError(f"pert requires min/mode/max ({params})")
        return _pert(rng, n, a, m, b, lam)

    if t == "triangular":
        a = _get(params, "min")
        m = _get(params, "mode")
        b = _get(params, "max")
        if a is None or m is None or b is None:
            raise DistError(f"triangular requires min/mode/max ({params})")
        return _triangular(rng, n, a, m, b)

    if t == "uniform":
        a = _get(params, "min")
        b = _get(params, "max")
        if a is None or b is None:
            raise DistError(f"uniform requires min/max ({params})")
        return _uniform(rng, n, a, b)

    if t == "normal":
        a = _get(params, "min")
        b = _get(params, "max")
        if a is None or b is None:
            raise DistError(f"normal requires min/max ({params})")
        return _normal(rng, n, a, b)

    if t == "lognormal":
        p10 = _get(params, "min")
        p90 = _get(params, "max")
        if p10 is None or p90 is None:
            raise DistError(f"lognormal requires min/max ({params})")
        return _lognormal(rng, n, p10, p90)

    if t == "beta":
        a = _get(params, "min", default=0.0) or 0.0
        b = _get(params, "max", default=1.0) or 1.0
        alpha = _get(params, "alpha", default=2.0) or 2.0
        beta_p = _get(params, "beta", default=5.0) or 5.0
        return _beta_dist(rng, n, a, b, alpha, beta_p)

    if t == "gamma":
        shape = _get(params, "shape", default=2.0) or 2.0
        a = _get(params, "min", default=0.0) or 0.0
        b = _get(params, "max", default=1.0) or 1.0
        scale = (b - a) / 6.0 if (b - a) > 0 else 1.0
        return _gamma(rng, n, shape, scale, offset=a)

    raise DistError(f"unknown distribution type: {t!r}")


def pdf_curve(params: dict[str, Any], grid_size: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """Approximate PDF for a distribution preview chart.

    Returns `(x, y)` arrays — `x` covers the support, `y` is the PDF height.
    """
    t = params.get("type", "pert")

    if t in {"pert", "triangular", "uniform", "normal", "lognormal"}:
        a = _get(params, "min")
        b = _get(params, "max")
        if a is None or b is None:
            raise DistError(f"{t} requires min/max for PDF curve")
        x = np.linspace(a, b, grid_size)
        if t == "pert":
            m = _get(params, "mode")
            lam = _get(params, "lambda", "lambda_", default=4.0) or 4.0
            alpha = 1 + lam * (m - a) / (b - a)
            beta = 1 + lam * (b - m) / (b - a)
            y = stats.beta.pdf((x - a) / (b - a), alpha, beta) / (b - a)
        elif t == "triangular":
            m = _get(params, "mode")
            y = stats.triang.pdf(x, c=(m - a) / (b - a), loc=a, scale=b - a)
        elif t == "uniform":
            y = stats.uniform.pdf(x, loc=a, scale=b - a)
        elif t == "normal":
            mean = (a + b) / 2.0
            sd = (b - a) / 6.0
            y = stats.norm.pdf(x, loc=mean, scale=sd)
        else:  # lognormal
            sigma = (np.log(b) - np.log(max(1.0, a))) / (Z90 - Z10)
            mu = np.log(max(1.0, a)) - Z10 * sigma
            x = np.linspace(max(1.0, a), b, grid_size)
            y = stats.lognorm.pdf(x, s=sigma, scale=np.exp(mu))
        return x, y

    if t == "beta":
        a = _get(params, "min", default=0.0) or 0.0
        b = _get(params, "max", default=1.0) or 1.0
        alpha = _get(params, "alpha", default=2.0) or 2.0
        beta_p = _get(params, "beta", default=5.0) or 5.0
        x = np.linspace(a, b, grid_size)
        y = stats.beta.pdf((x - a) / (b - a), alpha, beta_p) / (b - a)
        return x, y

    if t == "gamma":
        shape = _get(params, "shape", default=2.0) or 2.0
        a = _get(params, "min", default=0.0) or 0.0
        b = _get(params, "max", default=1.0) or 1.0
        scale = (b - a) / 6.0 if (b - a) > 0 else 1.0
        x = np.linspace(a, b, grid_size)
        y = stats.gamma.pdf(x - a, a=shape, scale=scale)
        return x, y

    raise DistError(f"unknown distribution type: {t!r}")
