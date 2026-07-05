"""Server-side session lifecycle — issue, validate, revoke, purge.

The signed cookie proves *who* the user claims to be and that the signature is
fresh; the `user_sessions` row is the server's authority on whether that token
is still live. Checking both means logout and deactivation take effect
immediately rather than waiting out the cookie TTL.
"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, delete, select

from app.config import settings
from app.models._base import utcnow
from app.models.session import UserSession


def issue(
    db: Session,
    *,
    user_id: int,
    token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> UserSession:
    row = UserSession(
        user_id=user_id,
        token=token,
        expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        user_agent=(user_agent or "")[:256] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(row)
    db.flush()
    return row


def is_live(db: Session, token: str) -> bool:
    """True if the token maps to a session that is neither revoked nor expired."""
    row = db.exec(select(UserSession).where(UserSession.token == token)).first()
    if row is None:
        return False
    if row.revoked_at is not None:
        return False
    if row.expires_at <= utcnow():
        return False
    return True


def revoke(db: Session, token: str) -> None:
    row = db.exec(select(UserSession).where(UserSession.token == token)).first()
    if row is not None and row.revoked_at is None:
        row.revoked_at = utcnow()
        db.flush()


def revoke_all_for_user(db: Session, user_id: int) -> int:
    """Revoke every live session for a user (used when deactivating an account)."""
    rows = db.exec(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .where(UserSession.revoked_at.is_(None))
    ).all()
    now = utcnow()
    for row in rows:
        row.revoked_at = now
    db.flush()
    return len(rows)


def purge_expired(db: Session) -> int:
    """Delete rows past their TTL (revoked or not). Called at startup + login."""
    cutoff = utcnow()
    result = db.exec(delete(UserSession).where(UserSession.expires_at <= cutoff))
    db.flush()
    # `rowcount` is available on the underlying result for DELETE.
    return getattr(result, "rowcount", 0) or 0
