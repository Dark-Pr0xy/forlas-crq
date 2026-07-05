"""Currency formatter spec compliance — matches fix.md §2 breakpoints."""

from __future__ import annotations

import pytest

from app.reporting.currency import (
    format_currency_aud as money,
    format_currency_aud_full as money_full,
    format_signed_money,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "A$0"),
        (999, "A$999"),
        (1_000, "A$1.0K"),
        (30_800, "A$30.8K"),
        (100_000, "A$100K"),  # >=100K drops the decimal
        (320_000, "A$320K"),
        (1_000_000, "A$1.0M"),
        (10_000_000, "A$10.0M"),
        (100_000_000, "A$100.0M"),
        (999_900_000, "A$999.9M"),
        (1_000_000_000, "A$1.0B"),
        (12_500_000_000, "A$12.5B"),
        (1_500_000_000_000, "A$1.5T"),
    ],
)
def test_money_breakpoints(value, expected):
    assert money(value) == expected


def test_money_handles_none_and_nan():
    assert money(None) == "—"
    assert money(float("nan")) == "—"


def test_money_negative_preserves_sign():
    assert money(-30_800) == "-A$30.8K"


def test_money_full_uses_thousands_separator():
    assert money_full(1_250_000) == "A$1,250,000"
    assert money_full(45_000) == "A$45,000"


def test_signed_money_prefixes_plus_or_minus():
    assert format_signed_money(50_000) == "+A$50.0K"
    assert format_signed_money(-50_000) == "-A$50.0K"
    assert format_signed_money(0) == "+A$0"


def test_no_usd_anywhere_in_output():
    for v in (1, 100, 1000, 1_000_000, 1_000_000_000):
        assert "USD" not in money(v)
        assert "US$" not in money(v)
        assert "$" in money(v)  # the dollar sign itself is fine — A$ contains it
