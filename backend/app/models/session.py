"""Server-side session records (for revocation + activity tracking)."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models._base import utcnow


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token: str = Field(index=True, unique=True, max_length=512)
    issued_at: datetime = Field(default_factory=utcnow, nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    revoked_at: datetime | None = Field(default=None)
    user_agent: str | None = Field(default=None, max_length=256)
    ip_address: str | None = Field(default=None, max_length=64)
