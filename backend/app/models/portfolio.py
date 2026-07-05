"""Portfolio aggregations and historical snapshots."""

from __future__ import annotations

from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import TimestampMixin, json_column, nullable_json_column


class Portfolio(TimestampMixin, SQLModel, table=True):
    """A named selection of scenarios with optional appetite/insurance settings."""

    __tablename__ = "portfolios"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=24)
    name: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=4000)
    scenario_public_ids: list[str] = Field(default_factory=list, sa_column=json_column())
    risk_appetite: float | None = Field(default=None)
    insurance_offset: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
    correlation_assumption: dict[str, Any] | None = Field(
        default=None, sa_column=nullable_json_column()
    )
    is_default: bool = Field(default=False, index=True)


class PortfolioSnapshot(TimestampMixin, SQLModel, table=True):
    """A point-in-time capture of portfolio totals.

    Mirrors the Alpha's `portfolioSnapshots` history but keyed properly.
    """

    __tablename__ = "portfolio_snapshots"

    id: int | None = Field(default=None, primary_key=True)
    portfolio_id: int | None = Field(default=None, foreign_key="portfolios.id", index=True)
    captured_by_user_id: int | None = Field(default=None, foreign_key="users.id")
    total_ale: float
    total_p50: float
    total_p90: float
    total_p95: float
    total_p99: float
    scenario_count: int
    simulated_count: int
    reason: str = Field(max_length=200)
    extras: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
