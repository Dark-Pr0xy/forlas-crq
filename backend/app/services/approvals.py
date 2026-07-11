"""Approval state machine for scenarios.

States:    draft → in_review → approved → archived
                                ↓
                              draft (rejected)

Re-opening from archived returns the scenario to draft.

RBAC: submit_for_review needs Reviewer; approve/reject needs Approver;
archive/reopen needs Owner. The router-layer dependency does the user check;
this service only enforces the *state* legality.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models._base import (
    ApprovalState,
    AuditAction,
    Role,
    utcnow,
)
from app.models.approval import ApprovalRequest, ReviewSchedule
from app.models.scenario import Scenario
from app.models.user import User
from app.services import audit
from app.services.ids import approval_id

Transition = Literal["submit_for_review", "approve", "reject", "archive", "reopen"]


_TRANSITIONS: dict[Transition, tuple[set[ApprovalState], ApprovalState, Role]] = {
    "submit_for_review": ({ApprovalState.DRAFT}, ApprovalState.IN_REVIEW, Role.REVIEWER),
    "approve": ({ApprovalState.IN_REVIEW}, ApprovalState.APPROVED, Role.APPROVER),
    "reject": ({ApprovalState.IN_REVIEW}, ApprovalState.DRAFT, Role.APPROVER),
    "archive": ({ApprovalState.APPROVED}, ApprovalState.ARCHIVED, Role.OWNER),
    "reopen": ({ApprovalState.ARCHIVED}, ApprovalState.DRAFT, Role.OWNER),
}


def required_role(action: Transition) -> Role:
    return _TRANSITIONS[action][2]


def separation_of_duties_enabled(db: Session) -> bool:
    """Whether the submitter-cannot-approve control is active (default on).

    Stored in ``AppSettings.extras['enforce_separation_of_duties']`` so a
    single-user local install can turn it off; multi-user installs keep it on.
    """
    from app.models.settings import AppSettings

    s = db.get(AppSettings, 1)
    if s is None or not s.extras:
        return True
    val = s.extras.get("enforce_separation_of_duties")
    return True if val is None else bool(val)


def _latest_submitter_id(db: Session, scenario: Scenario) -> int | None:
    """Who last submitted this scenario for review, if anyone."""
    row = db.exec(
        select(ApprovalRequest)
        .where(ApprovalRequest.entity_type == "scenario")
        .where(ApprovalRequest.entity_id == scenario.id)
        .where(ApprovalRequest.state == ApprovalState.IN_REVIEW)
        .order_by(ApprovalRequest.created_at.desc())
    ).first()
    return row.requested_by_user_id if row else None


def transition_scenario(
    db: Session,
    scenario: Scenario,
    *,
    action: Transition,
    actor: User,
    note: str | None = None,
    assigned_reviewer_user_id: int | None = None,
    request_id: str | None = None,
) -> ApprovalRequest:
    if action not in _TRANSITIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown transition: {action}")

    legal_from, target_state, required = _TRANSITIONS[action]
    if scenario.approval_state not in legal_from:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot {action} from state {scenario.approval_state.value}",
        )
    if Role.rank(actor.role) < Role.rank(required):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"{action} requires role >= {required.value}",
        )

    # Segregation of duties: whoever submitted a scenario for review must not be
    # the one who approves it. Applies regardless of role (even an Owner who
    # submitted cannot self-approve) unless the control is disabled in settings.
    if action == "approve" and separation_of_duties_enabled(db):
        submitter_id = _latest_submitter_id(db, scenario)
        if submitter_id is not None and submitter_id == actor.id:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Separation of duties: the person who submitted this scenario for "
                "review cannot approve it. A different approver must sign it off.",
            )

    prev_state = scenario.approval_state
    scenario.approval_state = target_state
    scenario.updated_at = utcnow()

    request = ApprovalRequest(
        public_id=approval_id(),
        entity_type="scenario",
        entity_id=scenario.id,
        requested_by_user_id=actor.id,
        assigned_reviewer_user_id=assigned_reviewer_user_id,
        state=target_state,
        request_note=note,
        decided_by_user_id=actor.id if action in {"approve", "reject", "archive"} else None,
        decided_at=utcnow() if action != "submit_for_review" else None,
    )
    db.add(request)
    db.flush()

    audit_action = {
        "submit_for_review": AuditAction.SUBMIT_FOR_REVIEW,
        "approve": AuditAction.APPROVE,
        "reject": AuditAction.REJECT,
        "archive": AuditAction.ARCHIVE,
        "reopen": AuditAction.UPDATE,
    }[action]
    audit.record(
        db,
        actor=actor,
        action=audit_action,
        entity_type="scenario",
        entity_id=scenario.public_id,
        summary=f"{action} · '{scenario.name}' · {prev_state.value} → {target_state.value}",
        before={"state": prev_state.value},
        after={"state": target_state.value, "note": note},
        request_id=request_id,
    )
    return request


# ---------------------------------------------------------------- schedules


def upsert_review_schedule(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    cadence_days: int,
    next_due: datetime,
) -> ReviewSchedule:
    existing = db.exec(
        select(ReviewSchedule)
        .where(ReviewSchedule.entity_type == entity_type)
        .where(ReviewSchedule.entity_id == entity_id)
    ).first()
    if existing:
        existing.cadence_days = cadence_days
        existing.next_due = next_due
        existing.active = True
        existing.updated_at = utcnow()
        db.flush()
        return existing
    sched = ReviewSchedule(
        entity_type=entity_type,
        entity_id=entity_id,
        cadence_days=cadence_days,
        next_due=next_due,
    )
    db.add(sched)
    db.flush()
    return sched


def mark_reviewed(
    db: Session, *, schedule: ReviewSchedule, actor: User
) -> ReviewSchedule:
    schedule.last_reviewed_at = utcnow()
    schedule.last_reviewed_by_user_id = actor.id
    schedule.next_due = utcnow() + timedelta(days=schedule.cadence_days)
    schedule.updated_at = utcnow()
    db.flush()
    return schedule


def overdue_schedules(db: Session, *, as_of: datetime | None = None) -> list[ReviewSchedule]:
    cutoff = as_of or utcnow()
    return list(
        db.exec(
            select(ReviewSchedule)
            .where(ReviewSchedule.active == True)  # noqa: E712
            .where(ReviewSchedule.next_due <= cutoff)
            .order_by(ReviewSchedule.next_due.asc())
        ).all()
    )
