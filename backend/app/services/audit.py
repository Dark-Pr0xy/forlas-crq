"""Append-only audit logging."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.models._base import AuditAction
from app.models.audit import AuditLog
from app.models.user import User


def record(
    db: Session,
    *,
    actor: User | None,
    action: AuditAction,
    entity_type: str,
    entity_id: str | int | None,
    summary: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_label=actor.display_name if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        before=before,
        after=after,
        request_id=request_id,
    )
    db.add(entry)
    db.flush()
    return entry
