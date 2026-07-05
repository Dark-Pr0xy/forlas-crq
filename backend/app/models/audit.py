"""Audit log — append-only record of every governance-relevant action."""

from __future__ import annotations

from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import AuditAction, TimestampMixin, nullable_json_column


class AuditLog(TimestampMixin, SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    actor_user_id: int | None = Field(default=None, foreign_key="users.id", index=True)
    actor_label: str | None = Field(default=None, max_length=120)
    action: AuditAction = Field(index=True)
    entity_type: str = Field(max_length=64, index=True)
    entity_id: str | None = Field(default=None, max_length=64, index=True)
    summary: str = Field(max_length=400)
    before: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
    after: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
    request_id: str | None = Field(default=None, max_length=64, index=True)
