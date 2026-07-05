"""Approval workflow records for scenarios and portfolios."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import ApprovalState, TimestampMixin, nullable_json_column


class ApprovalRequest(TimestampMixin, SQLModel, table=True):
    __tablename__ = "approval_requests"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=24)
    entity_type: str = Field(max_length=64, index=True)
    entity_id: int = Field(index=True)
    scenario_version_id: int | None = Field(
        default=None, foreign_key="scenario_versions.id", index=True
    )

    requested_by_user_id: int = Field(foreign_key="users.id", index=True)
    assigned_reviewer_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    state: ApprovalState = Field(default=ApprovalState.IN_REVIEW, index=True)
    request_note: str | None = Field(default=None, max_length=2000)

    decided_by_user_id: int | None = Field(default=None, foreign_key="users.id")
    decided_at: datetime | None = Field(default=None)
    decision_note: str | None = Field(default=None, max_length=2000)
    extras: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())


class ReviewSchedule(TimestampMixin, SQLModel, table=True):
    """Scheduled periodic review of a scenario or portfolio."""

    __tablename__ = "review_schedules"

    id: int | None = Field(default=None, primary_key=True)
    entity_type: str = Field(max_length=64, index=True)
    entity_id: int = Field(index=True)
    cadence_days: int = Field(default=90)
    next_due: datetime = Field(index=True)
    last_reviewed_at: datetime | None = Field(default=None)
    last_reviewed_by_user_id: int | None = Field(default=None, foreign_key="users.id")
    active: bool = Field(default=True, index=True)
