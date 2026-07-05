"""Simulation DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models._base import SimulationStatus


class SimulationRequest(BaseModel):
    # Upper bound mirrors settings.max_iterations (1M). Runs above the sync
    # ceiling are rejected at the service layer with a clear message.
    iterations: int | None = Field(default=None, ge=1_000, le=1_000_000)
    seed: int | None = None
    persist_artifacts: bool = True
    snapshot_scenario: bool = False
    snapshot_note: str | None = None


class SimulationStatistics(BaseModel):
    mean: float
    std: float
    p5: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float
    p99: float
    ci_lo: float
    ci_hi: float
    tail_mean: float
    zero_count: int
    iterations: int
    seed: int
    prob_exceed_tolerance: float
    tolerance: float
    tolerance_utilisation: float
    difference_to_tolerance: float


class SensitivityEntry(BaseModel):
    name: str
    label: str
    corr: float


class HistogramPayload(BaseModel):
    lo: float
    hi: float
    w: float
    counts: list[int]
    cap: float
    real_max: float
    tail_count: int
    tail_mean: float


class SimulationResultLight(BaseModel):
    id: str
    scenario_id: str
    status: SimulationStatus
    started_at: datetime | None
    completed_at: datetime | None
    progress: float
    iterations: int
    seed: int
    statistics: SimulationStatistics | None = None


class SimulationResultFull(SimulationResultLight):
    histogram: HistogramPayload | None = None
    lec_curve: list[list[float]] | None = None
    sensitivity: list[SensitivityEntry] | None = None
    losses_url: str | None = None  # Lazy load endpoint for raw loss vector
    driver_samples_url: str | None = None
    engine_version: str | None = None
    mode_at_run: str | None = None
    inputs_at_run: dict[str, Any] | None = None
