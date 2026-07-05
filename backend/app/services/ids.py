"""Short, URL-safe public IDs for stable cross-process references.

We use these instead of integer PKs in API contracts so DB renumbering or
import/export round-trips don't break references.
"""

from __future__ import annotations

import secrets

_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def short_id(prefix: str, length: int = 10) -> str:
    body = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}_{body}"


def scenario_id() -> str:
    return short_id("sc")


def simulation_id() -> str:
    return short_id("sim")


def portfolio_id() -> str:
    return short_id("pf")


def approval_id() -> str:
    return short_id("ap")
