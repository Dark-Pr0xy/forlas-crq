"""User accounts."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models._base import Role, TimestampMixin


class User(TimestampMixin, SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=320)
    display_name: str = Field(max_length=120)
    password_hash: str = Field(max_length=512)
    role: Role = Field(default=Role.READONLY, index=True)
    is_active: bool = Field(default=True, index=True)
    last_login_at: datetime | None = Field(default=None)
