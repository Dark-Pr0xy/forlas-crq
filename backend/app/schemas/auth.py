"""Auth-related DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models._base import Role


class LoginRequest(BaseModel):
    # Plain `str` rather than `EmailStr`: this is a local-only app and we want
    # to allow trivial accounts like `owner@local` without a registered TLD.
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    id: int
    email: str
    display_name: str
    role: Role
    is_active: bool
    last_login_at: datetime | None = None


class LoginResponse(BaseModel):
    """Login result. `session_token` lets non-cookie clients (the Tauri
    WebView) authenticate via the X-Session-Token header."""

    user: UserPublic
    session_token: str


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: Role = Role.READONLY


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)


class SessionStatus(BaseModel):
    authenticated: bool
    user: UserPublic | None = None
    ula_acknowledged: bool = False
    ula_version: str | None = None
