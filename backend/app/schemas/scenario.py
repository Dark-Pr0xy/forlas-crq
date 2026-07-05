"""Scenario DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.models._base import ApprovalState, DecompositionMode, DistributionType


class DistributionParam(BaseModel):
    """A single distribution parameter block (one of the input variables)."""

    type: DistributionType
    min: float | None = None
    mode: float | None = None
    max: float | None = None
    alpha: float | None = None
    beta: float | None = None
    shape: float | None = None
    lambda_: float | None = Field(default=None, alias="lambda")
    notes: str | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _sanity_check(self) -> "DistributionParam":
        if self.type in {
            DistributionType.PERT,
            DistributionType.TRIANGULAR,
        }:
            if self.min is None or self.mode is None or self.max is None:
                raise ValueError(f"{self.type.value} requires min/mode/max")
            if not (self.min <= self.mode <= self.max):
                raise ValueError(f"{self.type.value} requires min <= mode <= max")
        if self.type in {
            DistributionType.UNIFORM,
            DistributionType.NORMAL,
            DistributionType.LOGNORMAL,
        }:
            if self.min is None or self.max is None:
                raise ValueError(f"{self.type.value} requires min/max")
        if self.type == DistributionType.BETA and (self.alpha is None or self.beta is None):
            raise ValueError("beta requires alpha and beta")
        if self.type == DistributionType.GAMMA and self.shape is None:
            raise ValueError("gamma requires shape")
        return self


class ScenarioInputs(BaseModel):
    """The full set of distribution parameters used by the simulation engine."""

    lef: DistributionParam | None = None
    tef: DistributionParam | None = None
    vuln: DistributionParam | None = None
    tcap: DistributionParam | None = None
    rs: DistributionParam | None = None
    plm: DistributionParam
    slp_prob: DistributionParam
    slm: DistributionParam


class ReferenceLine(BaseModel):
    label: str
    value: float
    color: str = "#7A92F4"


class ScenarioBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    business_unit: str | None = None
    scenario_type: str | None = None
    benchmark_group: str | None = None
    tags: list[str] = Field(default_factory=list)
    owner_label: str | None = None
    mode: DecompositionMode = DecompositionMode.TEF_VULN
    inputs: ScenarioInputs
    tolerance: float = 0.0
    reduction_pct: float = 0.0
    reference_lines: list[ReferenceLine] = Field(default_factory=list)
    prefs: dict[str, Any] = Field(default_factory=dict)
    version_label: str = "1.0"
    assessment_date: str | None = None
    review_date: str | None = None
    threat_refs: list[str] = Field(default_factory=list)
    control_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class ScenarioCreate(ScenarioBase):
    pass


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    business_unit: str | None = None
    scenario_type: str | None = None
    benchmark_group: str | None = None
    tags: list[str] | None = None
    owner_label: str | None = None
    mode: DecompositionMode | None = None
    inputs: ScenarioInputs | None = None
    tolerance: float | None = None
    reduction_pct: float | None = None
    reference_lines: list[ReferenceLine] | None = None
    prefs: dict[str, Any] | None = None
    version_label: str | None = None
    assessment_date: str | None = None
    review_date: str | None = None
    threat_refs: list[str] | None = None
    control_refs: list[str] | None = None
    notes: str | None = None
    snapshot_note: str | None = None  # If provided, save a ScenarioVersion record


class ScenarioRead(ScenarioBase):
    id: str  # public_id
    approval_state: ApprovalState
    owner_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    latest_simulation_id: str | None = None


class ScenarioVersionRead(BaseModel):
    id: int
    scenario_id: str
    version_label: str
    note: str | None
    author_user_id: int | None
    created_at: datetime


class ApprovalTransitionRequest(BaseModel):
    action: Literal["submit_for_review", "approve", "reject", "archive", "reopen"]
    note: str | None = None
    assigned_reviewer_user_id: int | None = None
