"""Single source of truth for currency formatting (AUD).

Matches the breakpoints in `frontend/src/lib/format.ts` so HTML / DOCX
reports show identical strings to the on-screen UI.
"""

from __future__ import annotations

import math
from typing import Any

CURRENCY_PREFIX = "A$"


def format_currency_aud(value: Any) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(v) or math.isinf(v):
        return "—"
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a < 1_000:
        return f"{sign}{CURRENCY_PREFIX}{round(a)}"
    if a < 100_000:
        return f"{sign}{CURRENCY_PREFIX}{a / 1_000:.1f}K"
    if a < 1_000_000:
        return f"{sign}{CURRENCY_PREFIX}{round(a / 1_000)}K"
    if a < 1_000_000_000:
        return f"{sign}{CURRENCY_PREFIX}{a / 1_000_000:.1f}M"
    if a < 1_000_000_000_000:
        return f"{sign}{CURRENCY_PREFIX}{a / 1_000_000_000:.1f}B"
    return f"{sign}{CURRENCY_PREFIX}{a / 1_000_000_000_000:.1f}T"


def format_currency_aud_full(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{CURRENCY_PREFIX}{round(float(value)):,}"
    except (TypeError, ValueError):
        return "—"


def format_signed_money(value: Any) -> str:
    """Plus/minus prefixed monetary delta — for 'Δ from mean' style columns."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if v >= 0 else "-"
    return f"{sign}{format_currency_aud(abs(v))}"
