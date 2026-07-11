"""Analysis & evidence CRUD (one record per scenario)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models._base import ApprovalState, AuditAction, utcnow
from app.models.analysis import AnalysisRecord
from app.models.scenario import Scenario
from app.models.user import User
from app.schemas.analysis import AnalysisUpdate
from app.services import audit
from app.services.scenario import require_can_modify


def get_record(db: Session, scenario: Scenario) -> AnalysisRecord | None:
    return db.exec(
        select(AnalysisRecord).where(AnalysisRecord.scenario_id == scenario.id)
    ).first()


def _to_read(scenario: Scenario, rec: AnalysisRecord | None) -> dict[str, Any]:
    if rec is None:
        return {
            "scenario_id": scenario.public_id,
            "summary": None,
            "confidence": None,
            "data_sources": [],
            "assumptions": [],
            "gaps": [],
            "input_rationale": {},
            "updated_at": None,
            "updated_by_user_id": None,
        }
    return {
        "scenario_id": scenario.public_id,
        "summary": rec.summary,
        "confidence": rec.confidence,
        "data_sources": list(rec.data_sources or []),
        "assumptions": list(rec.assumptions or []),
        "gaps": list(rec.gaps or []),
        "input_rationale": dict(rec.input_rationale or {}),
        "updated_at": rec.updated_at,
        "updated_by_user_id": rec.updated_by_user_id,
    }


def read_analysis(db: Session, scenario: Scenario) -> dict[str, Any]:
    return _to_read(scenario, get_record(db, scenario))


def upsert_analysis(
    db: Session,
    scenario: Scenario,
    payload: AnalysisUpdate,
    *,
    actor: User,
    request_id: str | None = None,
) -> dict[str, Any]:
    # Same gate as scenario edits (H2): the owner or an Approver+ may write.
    require_can_modify(scenario, actor)
    # And the analysis backing an approved/archived scenario is part of the
    # approved package — reopen to draft before changing the evidence (H1).
    if scenario.approval_state in (ApprovalState.APPROVED, ApprovalState.ARCHIVED):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Scenario is '{scenario.approval_state.value}'. Reopen it to draft "
            f"before changing its analysis & evidence.",
        )

    rec = get_record(db, scenario)
    created = rec is None
    if rec is None:
        rec = AnalysisRecord(scenario_id=scenario.id)
        db.add(rec)

    data = payload.model_dump(exclude_unset=True)
    if "summary" in data:
        rec.summary = data["summary"]
    if "confidence" in data:
        rec.confidence = data["confidence"]
    if "data_sources" in data and data["data_sources"] is not None:
        rec.data_sources = [d.model_dump() for d in (payload.data_sources or [])]
    if "assumptions" in data and data["assumptions"] is not None:
        rec.assumptions = [a.model_dump() for a in (payload.assumptions or [])]
    if "gaps" in data and data["gaps"] is not None:
        rec.gaps = [g.model_dump() for g in (payload.gaps or [])]
    if "input_rationale" in data and data["input_rationale"] is not None:
        # Drop blank entries so the store stays tidy.
        rec.input_rationale = {
            k: v for k, v in (payload.input_rationale or {}).items() if (v or "").strip()
        }
    rec.updated_by_user_id = actor.id
    rec.updated_at = utcnow()
    db.flush()

    audit.record(
        db,
        actor=actor,
        action=AuditAction.CREATE if created else AuditAction.UPDATE,
        entity_type="scenario.analysis",
        entity_id=scenario.public_id,
        summary=f"{'Recorded' if created else 'Updated'} analysis & evidence for '{scenario.name}'",
        request_id=request_id,
    )
    return _to_read(scenario, rec)
