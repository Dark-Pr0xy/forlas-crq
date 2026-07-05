"""Simulation runs and their results.

Each `SimulationRun` is a single Monte Carlo execution for a scenario at a
specific seed/iteration setting. Heavyweight arrays (losses, sorted losses,
LEC curve, histogram) live in `SimulationArtifact`, opaque to ORM queries so
we don't pay JSON parsing on every list view.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import (
    SimulationStatus,
    TimestampMixin,
    json_column,
    nullable_json_column,
)


class SimulationRun(TimestampMixin, SQLModel, table=True):
    __tablename__ = "simulation_runs"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=24)
    scenario_id: int = Field(foreign_key="scenarios.id", index=True)
    scenario_version_id: int | None = Field(
        default=None, foreign_key="scenario_versions.id", index=True
    )
    triggered_by_user_id: int | None = Field(default=None, foreign_key="users.id")

    iterations: int
    seed: int
    status: SimulationStatus = Field(default=SimulationStatus.PENDING, index=True)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None, index=True)
    progress: float = Field(default=0.0)
    error_message: str | None = Field(default=None, max_length=4000)

    # Headline statistics (denormalised for fast list views)
    mean: float | None = Field(default=None)
    std: float | None = Field(default=None)
    p5: float | None = Field(default=None)
    p25: float | None = Field(default=None)
    p50: float | None = Field(default=None)
    p75: float | None = Field(default=None)
    p90: float | None = Field(default=None)
    p95: float | None = Field(default=None)
    p99: float | None = Field(default=None)
    ci_lo: float | None = Field(default=None)
    ci_hi: float | None = Field(default=None)
    tail_mean: float | None = Field(default=None)
    zero_count: int | None = Field(default=None)
    prob_exceed_tolerance: float | None = Field(default=None)
    tolerance_at_run: float | None = Field(default=None)

    # Captured at run-time for reproducibility
    inputs_at_run: dict[str, Any] = Field(sa_column=json_column())
    mode_at_run: str = Field(max_length=16)
    engine_version: str = Field(max_length=32)
    sensitivity: list[dict[str, Any]] | None = Field(default=None, sa_column=nullable_json_column())


class SimulationArtifact(SQLModel, table=True):
    """One-to-one heavy payload for a SimulationRun.

    `losses` is the raw per-iteration vector; `sorted_losses` is its sort;
    `histogram` and `lec_curve` are the display-ready precomputations from the
    engine. Stored as JSON blobs (compact binary backing in SQLite TEXT).
    """

    __tablename__ = "simulation_artifacts"

    simulation_run_id: int = Field(foreign_key="simulation_runs.id", primary_key=True)
    losses: list[float] = Field(sa_column=json_column())
    sorted_losses: list[float] = Field(sa_column=json_column())
    lefs: list[float] = Field(sa_column=json_column())
    histogram: dict[str, Any] = Field(sa_column=json_column())
    lec_curve: list[list[float]] = Field(sa_column=json_column())
    driver_samples: dict[str, list[float]] | None = Field(
        default=None, sa_column=nullable_json_column()
    )
