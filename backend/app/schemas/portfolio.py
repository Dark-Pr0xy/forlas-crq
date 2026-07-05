"""Portfolio DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PortfolioBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    scenario_public_ids: list[str] = Field(default_factory=list)
    risk_appetite: float | None = None
    insurance_offset: dict[str, Any] | None = None
    correlation_assumption: dict[str, Any] | None = None
    is_default: bool = False


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    scenario_public_ids: list[str] | None = None
    risk_appetite: float | None = None
    insurance_offset: dict[str, Any] | None = None
    correlation_assumption: dict[str, Any] | None = None
    is_default: bool | None = None


class PortfolioRead(PortfolioBase):
    id: str
    created_at: datetime
    updated_at: datetime


class PortfolioRollup(BaseModel):
    """Aggregated portfolio metrics derived from current simulations."""

    portfolio_id: str | None
    scenario_count: int
    simulated_count: int
    total_ale: float
    total_p50: float
    total_p90: float
    total_p95: float
    total_p99: float
    total_tail: float
    over_tolerance_count: int
    appetite: float | None
    appetite_utilisation: float | None
    lec_curve: list[list[float]] = Field(default_factory=list)
    top_scenarios: list[dict[str, Any]] = Field(default_factory=list)


class SnapshotRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=200)
    portfolio_id: str | None = None
