"""Application-level settings persisted to the DB (single row).

Distinct from `app.config.Settings` (env vars). This is user-mutable runtime
state: default seed/iterations, theme preference, ULA acknowledgement etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import TimestampMixin, nullable_json_column


class AppSettings(TimestampMixin, SQLModel, table=True):
    __tablename__ = "app_settings"

    id: int | None = Field(default=1, primary_key=True)
    iterations: int = Field(default=100_000)
    seed: int = Field(default=42)
    ula_acknowledged_version: str | None = Field(default=None, max_length=32)
    ula_acknowledged_at: datetime | None = Field(default=None)
    ula_acknowledged_by_user_id: int | None = Field(default=None, foreign_key="users.id")
    theme: str = Field(default="light", max_length=16)
    extras: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())
