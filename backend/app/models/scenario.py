"""Scenarios and their immutable versioned snapshots.

A `Scenario` is the editable, current-state container — what the workspace
binds to. Each save can spawn a `ScenarioVersion`, which is an immutable copy
of the inputs / metadata at that point, used for audit and approval history.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import (
    ApprovalState,
    DecompositionMode,
    TimestampMixin,
    json_column,
    nullable_json_column,
)


class Scenario(TimestampMixin, SQLModel, table=True):
    __tablename__ = "scenarios"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=24)
    name: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=4000)

    # Categorisation
    business_unit: str | None = Field(default=None, max_length=120, index=True)
    scenario_type: str | None = Field(default=None, max_length=80, index=True)
    benchmark_group: str | None = Field(default=None, max_length=120)
    tags: list[str] = Field(default_factory=list, sa_column=json_column())

    # Ownership
    owner_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    owner_label: str | None = Field(default=None, max_length=120)  # free-text "owner" name

    # Modelling
    mode: DecompositionMode = Field(default=DecompositionMode.TEF_VULN, index=True)
    inputs: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())
    tolerance: float = Field(default=0.0)
    reduction_pct: float = Field(default=0.0)
    reference_lines: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())
    prefs: dict[str, Any] = Field(default_factory=dict, sa_column=json_column())

    # Lifecycle
    version_label: str = Field(default="1.0", max_length=16)
    assessment_date: str | None = Field(default=None, max_length=24)
    review_date: str | None = Field(default=None, max_length=24)
    approval_state: ApprovalState = Field(default=ApprovalState.DRAFT, index=True)

    # Linked references
    threat_refs: list[str] = Field(default_factory=list, sa_column=json_column())
    control_refs: list[str] = Field(default_factory=list, sa_column=json_column())

    notes: str | None = Field(default=None, max_length=8000)
    deleted_at: str | None = Field(default=None, index=True)


class ScenarioVersion(TimestampMixin, SQLModel, table=True):
    __tablename__ = "scenario_versions"

    id: int | None = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenarios.id", index=True)
    version_label: str = Field(max_length=16)
    snapshot: dict[str, Any] = Field(sa_column=json_column())  # full scenario state
    author_user_id: int | None = Field(default=None, foreign_key="users.id")
    note: str | None = Field(default=None, max_length=2000)
    diff: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
