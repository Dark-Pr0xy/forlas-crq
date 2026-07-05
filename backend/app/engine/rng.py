"""Deterministic RNG.

NumPy's PCG64 — high statistical quality, fast vectorised sampling, seeded for
reproducibility. Identical seed + identical scenario ⇒ identical results.

(A JS-compatible Mulberry32 port was removed: it was unused, untested, and its
"Alpha parity" claim was never verified — shipping it invited false trust. If
bit-exact Alpha reproduction is ever needed, add it back behind real parity
tests against known JS outputs.)
"""

from __future__ import annotations

import numpy as np


def default_rng(seed: int) -> np.random.Generator:
    """Primary RNG — PCG64. Use this for production simulations."""
    return np.random.default_rng(seed)
