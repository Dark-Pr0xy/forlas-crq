"""FastAPI dependencies: DB session, current user, RBAC guards."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.models._base import Role
from app.models.user import User
from app.security import verify_session
from app.services import sessions as session_svc

SessionDep = Annotated[Session, Depends(get_session)]

# Header used when a cookie can't be relied on (the Tauri WebView talks to the
# backend cross-origin, where SameSite cookies aren't sent). The frontend sends
# the token it got from /login here; same token, same server-side session row.
SESSION_HEADER = "X-Session-Token"


def _resolve_user(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    user_id = verify_session(token)
    if user_id is None:
        return None
    # The signature is fresh — but the server-side record is the authority on
    # whether this token is still live (not logged out, not revoked, not expired).
    if not session_svc.is_live(db, token):
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user_optional(
    db: SessionDep,
    session_token: Annotated[str | None, Cookie(alias=settings.session_cookie_name)] = None,
    header_token: Annotated[str | None, Header(alias=SESSION_HEADER)] = None,
) -> User | None:
    # Cookie first (same-origin dev/Docker), then header (Tauri cross-origin).
    return _resolve_user(db, session_token or header_token)


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return user


def require_role(minimum: Role):
    """Dependency factory enforcing a minimum role on the current user."""

    def _guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        if Role.rank(user.role) < Role.rank(minimum):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role >= {minimum.value}")
        return user

    return _guard


CurrentUser = Annotated[User, Depends(get_current_user)]
ReviewerUser = Annotated[User, Depends(require_role(Role.REVIEWER))]
ApproverUser = Annotated[User, Depends(require_role(Role.APPROVER))]
OwnerUser = Annotated[User, Depends(require_role(Role.OWNER))]


def request_id_dep(request: Request) -> str:
    rid = request.headers.get("x-request-id")
    if rid:
        return rid
    # Generate a short, ULID-ish per-request id; not crypto-secure.
    import secrets

    return secrets.token_hex(8)


RequestId = Annotated[str, Depends(request_id_dep)]
