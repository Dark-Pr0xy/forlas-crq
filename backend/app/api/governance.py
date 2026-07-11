"""Governance endpoints — audit log, approvals, review schedules, change history."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select

from app.deps import CurrentUser, RequestId, ReviewerUser, SessionDep
from app.models._base import AuditAction
from app.models.approval import ApprovalRequest, ReviewSchedule
from app.models.audit import AuditLog
from app.models.scenario import Scenario, ScenarioVersion
from app.services import approvals as approval_svc
from app.services import scenario as scn_svc

router = APIRouter(prefix="/api/governance", tags=["governance"])


# ----------------------------------------------------------------- audit log


class AuditEntry(BaseModel):
    id: int
    actor_label: str | None
    action: AuditAction
    entity_type: str
    entity_id: str | None
    summary: str
    request_id: str | None
    created_at: datetime
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


@router.get("/audit", response_model=list[AuditEntry])
def list_audit(
    db: SessionDep,
    _: CurrentUser,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    entity_type: str | None = None,
    entity_id: str | None = None,
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    return [AuditEntry.model_validate(row, from_attributes=True) for row in db.exec(stmt).all()]


# ----------------------------------------------------------------- approvals


class ApprovalTransition(BaseModel):
    action: Literal["submit_for_review", "approve", "reject", "archive", "reopen"]
    note: str | None = None
    assigned_reviewer_user_id: int | None = None


class ApprovalRequestRead(BaseModel):
    id: str
    entity_type: str
    entity_id: int
    state: str
    requested_by_user_id: int
    assigned_reviewer_user_id: int | None
    request_note: str | None
    decided_by_user_id: int | None
    decided_at: datetime | None
    decision_note: str | None
    created_at: datetime


@router.post(
    "/scenarios/{scenario_id}/transition",
    response_model=ApprovalRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def transition_scenario(
    scenario_id: str,
    payload: ApprovalTransition,
    db: SessionDep,
    user: CurrentUser,
    request_id: RequestId,
):
    scn = scn_svc.get_scenario(db, scenario_id)
    request = approval_svc.transition_scenario(
        db,
        scn,
        action=payload.action,
        actor=user,
        note=payload.note,
        assigned_reviewer_user_id=payload.assigned_reviewer_user_id,
        request_id=request_id,
    )
    db.commit()
    return ApprovalRequestRead(
        id=request.public_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        state=request.state.value,
        requested_by_user_id=request.requested_by_user_id,
        assigned_reviewer_user_id=request.assigned_reviewer_user_id,
        request_note=request.request_note,
        decided_by_user_id=request.decided_by_user_id,
        decided_at=request.decided_at,
        decision_note=request.decision_note,
        created_at=request.created_at,
    )


@router.get("/approvals", response_model=list[ApprovalRequestRead])
def list_approvals(
    db: SessionDep,
    _: CurrentUser,
    limit: int = Query(100, ge=1, le=500),
):
    rows = db.exec(
        select(ApprovalRequest)
        .order_by(ApprovalRequest.created_at.desc())
        .limit(limit)
    ).all()
    return [
        ApprovalRequestRead(
            id=r.public_id,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            state=r.state.value,
            requested_by_user_id=r.requested_by_user_id,
            assigned_reviewer_user_id=r.assigned_reviewer_user_id,
            request_note=r.request_note,
            decided_by_user_id=r.decided_by_user_id,
            decided_at=r.decided_at,
            decision_note=r.decision_note,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ----------------------------------------------------------------- schedules


class ScheduleUpsert(BaseModel):
    cadence_days: int
    next_due: datetime | None = None


class ScheduleRead(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    cadence_days: int
    next_due: datetime
    last_reviewed_at: datetime | None
    last_reviewed_by_user_id: int | None
    active: bool


@router.put(
    "/scenarios/{scenario_id}/schedule",
    response_model=ScheduleRead,
)
def upsert_schedule(
    scenario_id: str,
    payload: ScheduleUpsert,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scn = scn_svc.get_scenario(db, scenario_id)
    sched = approval_svc.upsert_review_schedule(
        db,
        entity_type="scenario",
        entity_id=scn.id,
        cadence_days=payload.cadence_days,
        next_due=payload.next_due or (datetime.utcnow() + timedelta(days=payload.cadence_days)),
    )
    db.commit()
    return ScheduleRead.model_validate(sched, from_attributes=True)


@router.post(
    "/scenarios/{scenario_id}/schedule/mark-reviewed",
    response_model=ScheduleRead,
)
def mark_reviewed(
    scenario_id: str,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scn = scn_svc.get_scenario(db, scenario_id)
    sched = db.exec(
        select(ReviewSchedule)
        .where(ReviewSchedule.entity_type == "scenario")
        .where(ReviewSchedule.entity_id == scn.id)
    ).first()
    if sched is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No schedule configured")
    approval_svc.mark_reviewed(db, schedule=sched, actor=user)
    db.commit()
    return ScheduleRead.model_validate(sched, from_attributes=True)


@router.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(db: SessionDep, _: CurrentUser):
    rows = db.exec(select(ReviewSchedule).order_by(ReviewSchedule.next_due.asc())).all()
    return [ScheduleRead.model_validate(r, from_attributes=True) for r in rows]


@router.get("/schedules/overdue", response_model=list[ScheduleRead])
def list_overdue(db: SessionDep, _: CurrentUser):
    rows = approval_svc.overdue_schedules(db)
    return [ScheduleRead.model_validate(r, from_attributes=True) for r in rows]


# ------------------------------------------------------------------- reviews
#
# Reviews driven by each scenario's `review_date` field — the value users
# actually set in the workspace metadata panel. This is distinct from the
# cadence-based ReviewSchedule table above (kept for programmatic use); this
# endpoint is what the governance UI surfaces so a review date set on a
# scenario shows up as "current" (future) or "overdue" (past) immediately.


class ReviewItem(BaseModel):
    scenario_id: str
    name: str
    business_unit: str | None
    owner_label: str | None
    approval_state: str
    assessment_date: str | None
    review_date: str | None
    overdue: bool
    days_until: int | None  # negative when overdue; None when no date set


@router.get("/reviews", response_model=list[ReviewItem])
def list_reviews(db: SessionDep, _: CurrentUser):
    rows = db.exec(select(Scenario).where(Scenario.deleted_at.is_(None))).all()
    today = date.today()
    today_iso = today.isoformat()
    items: list[ReviewItem] = []
    for s in rows:
        rd = (s.review_date or "").strip() or None
        overdue = rd is not None and rd[:10] < today_iso
        days: int | None = None
        if rd is not None:
            try:
                days = (date.fromisoformat(rd[:10]) - today).days
            except ValueError:
                days = None
        items.append(
            ReviewItem(
                scenario_id=s.public_id,
                name=s.name,
                business_unit=s.business_unit,
                owner_label=s.owner_label,
                approval_state=s.approval_state.value,
                assessment_date=s.assessment_date,
                review_date=rd,
                overdue=overdue,
                days_until=days,
            )
        )

    def _sort_key(it: ReviewItem) -> tuple[int, int]:
        if it.review_date is None:
            return (2, 0)  # undated last
        if it.overdue:
            return (0, it.days_until or 0)  # overdue first, most overdue first
        return (1, it.days_until or 0)  # upcoming, soonest first

    items.sort(key=_sort_key)
    return items


# ----------------------------------------------------------------- change history


class VersionEntry(BaseModel):
    id: int
    scenario_id: str
    version_label: str
    note: str | None
    author_user_id: int | None
    created_at: datetime


@router.get(
    "/scenarios/{scenario_id}/versions",
    response_model=list[VersionEntry],
)
def list_versions(scenario_id: str, db: SessionDep, _: CurrentUser):
    scn = scn_svc.get_scenario(db, scenario_id)
    rows = db.exec(
        select(ScenarioVersion)
        .where(ScenarioVersion.scenario_id == scn.id)
        .order_by(ScenarioVersion.created_at.desc())
    ).all()
    return [
        VersionEntry(
            id=v.id,
            scenario_id=scn.public_id,
            version_label=v.version_label,
            note=v.note,
            author_user_id=v.author_user_id,
            created_at=v.created_at,
        )
        for v in rows
    ]
