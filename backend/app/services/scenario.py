"""Scenario CRUD + versioning helpers."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models._base import ApprovalState, AuditAction, Role, utcnow
from app.models.scenario import Scenario, ScenarioVersion
from app.models.user import User
from app.schemas.scenario import ScenarioCreate, ScenarioRead, ScenarioUpdate
from app.services import audit
from app.services.ids import scenario_id

# Fields that change the analysis itself — locked once a scenario leaves draft.
_MODELLING_FIELDS = {"mode", "inputs", "tolerance", "reduction_pct"}

# Pre-canned scenario categories offered in the workspace type picker. Users can
# add their own; those persist in AppSettings.extras["scenario_types"].
DEFAULT_SCENARIO_TYPES = [
    "Ransomware",
    "Business Email Compromise",
    "Phishing / Social Engineering",
    "Insider Threat",
    "Data Breach / PII Exposure",
    "Web Application Exploit",
    "Cloud Misconfiguration",
    "Denial of Service / Availability",
    "Third Party / Supply Chain",
    "Malware",
    "Fraud",
    "Physical / Environmental",
]


def _dedupe_preserve(items: list[str]) -> list[str]:
    """Trim, drop blanks, and case-insensitively de-duplicate, keeping order."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        val = (raw or "").strip()
        key = val.lower()
        if not val or key in seen:
            continue
        seen.add(key)
        out.append(val)
    return out


def list_scenario_types(db: Session) -> list[str]:
    """Presets first, then any user-added or in-use types (alphabetical)."""
    from app.models.settings import AppSettings

    s = db.get(AppSettings, 1)
    custom = list((s.extras or {}).get("scenario_types") or []) if s and s.extras else []
    used = [t for t in db.exec(select(Scenario.scenario_type).distinct()).all() if t]

    result = _dedupe_preserve(DEFAULT_SCENARIO_TYPES)
    known = {r.lower() for r in result}
    for other in sorted(_dedupe_preserve([*custom, *used]), key=str.lower):
        if other.lower() not in known:
            result.append(other)
            known.add(other.lower())
    return result


def add_scenario_type(db: Session, name: str) -> tuple[list[str], bool]:
    """Persist a user-supplied scenario type, unless it duplicates a preset or
    an existing custom entry. Returns (full updated list, whether it was new)."""
    from app.services.seed import ensure_app_settings

    label = (name or "").strip()
    if not label:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Scenario type name is required")
    if len(label) > 80:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Scenario type is too long (max 80)")

    existing = {t.lower() for t in list_scenario_types(db)}
    added = label.lower() not in existing
    if added:
        s = ensure_app_settings(db)
        extras = dict(s.extras or {})
        types = list(extras.get("scenario_types") or [])
        types.append(label)
        extras["scenario_types"] = types
        s.extras = extras  # reassign so the JSON column change is tracked
        s.updated_at = utcnow()
        db.flush()
    return list_scenario_types(db), added


def _dump_inputs(payload) -> dict[str, Any]:
    """Convert nested Pydantic distribution params into a plain JSON dict."""
    return json.loads(payload.model_dump_json(by_alias=True))


def require_can_modify(scn: Scenario, actor: User) -> None:
    """Ownership gate (H2): the owner or an Approver+ may modify/delete.

    Reviewers who don't own the scenario are read-through for it. Approvers and
    Owners can act on any scenario (they're the escalation path).
    """
    if Role.rank(actor.role) >= Role.rank(Role.APPROVER):
        return
    if scn.owner_user_id is not None and scn.owner_user_id == actor.id:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Only the scenario owner or an Approver can modify this scenario.",
    )


def _require_draft_for_modelling(scn: Scenario, changed_fields: set[str]) -> None:
    """Analysis-lock gate (H1): modelling fields can't change unless draft."""
    if scn.approval_state == ApprovalState.DRAFT:
        return
    if changed_fields & _MODELLING_FIELDS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Scenario is '{scn.approval_state.value}'. Reopen it to draft before "
            f"changing its model (inputs / mode / tolerance / reduction).",
        )


def list_scenarios(db: Session, *, include_deleted: bool = False) -> list[Scenario]:
    stmt = select(Scenario).order_by(Scenario.updated_at.desc())
    if not include_deleted:
        stmt = stmt.where(Scenario.deleted_at.is_(None))
    return list(db.exec(stmt).all())


def get_scenario(db: Session, public_id: str) -> Scenario:
    scn = db.exec(select(Scenario).where(Scenario.public_id == public_id)).first()
    if scn is None or scn.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    return scn


def create_scenario(
    db: Session, payload: ScenarioCreate, *, actor: User, request_id: str | None = None
) -> Scenario:
    scn = Scenario(
        public_id=scenario_id(),
        owner_user_id=actor.id,
        **payload.model_dump(exclude={"inputs", "reference_lines"}),
        inputs=_dump_inputs(payload.inputs),
        reference_lines=[r.model_dump() for r in payload.reference_lines],
    )
    db.add(scn)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="scenario",
        entity_id=scn.public_id,
        summary=f"Created scenario '{scn.name}'",
        after=ScenarioRead.model_validate(_to_read(scn)).model_dump(mode="json"),
        request_id=request_id,
    )
    return scn


def update_scenario(
    db: Session,
    public_id: str,
    payload: ScenarioUpdate,
    *,
    actor: User,
    request_id: str | None = None,
) -> Scenario:
    scn = get_scenario(db, public_id)
    require_can_modify(scn, actor)
    before = ScenarioRead.model_validate(_to_read(scn)).model_dump(mode="json")
    data = payload.model_dump(exclude_unset=True, exclude={"snapshot_note"})
    _require_draft_for_modelling(scn, set(data.keys()))

    if "inputs" in data and data["inputs"] is not None:
        data["inputs"] = _dump_inputs(payload.inputs)
    if "reference_lines" in data and data["reference_lines"] is not None:
        data["reference_lines"] = [r.model_dump() for r in payload.reference_lines]

    for k, v in data.items():
        setattr(scn, k, v)
    scn.updated_at = utcnow()

    if payload.snapshot_note is not None:
        snapshot = ScenarioVersion(
            scenario_id=scn.id,
            version_label=scn.version_label,
            snapshot=ScenarioRead.model_validate(_to_read(scn)).model_dump(mode="json"),
            author_user_id=actor.id,
            note=payload.snapshot_note,
        )
        db.add(snapshot)

    db.flush()
    after = ScenarioRead.model_validate(_to_read(scn)).model_dump(mode="json")
    audit.record(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="scenario",
        entity_id=scn.public_id,
        summary=f"Updated scenario '{scn.name}'",
        before=before,
        after=after,
        request_id=request_id,
    )
    return scn


def soft_delete_scenario(
    db: Session, public_id: str, *, actor: User, request_id: str | None = None
) -> None:
    scn = get_scenario(db, public_id)
    require_can_modify(scn, actor)
    scn.deleted_at = utcnow().isoformat()
    scn.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.DELETE,
        entity_type="scenario",
        entity_id=scn.public_id,
        summary=f"Deleted scenario '{scn.name}'",
        request_id=request_id,
    )


def restore_scenario(
    db: Session, public_id: str, *, actor: User, request_id: str | None = None
) -> Scenario:
    """Undo a soft-delete (M8)."""
    scn = db.exec(select(Scenario).where(Scenario.public_id == public_id)).first()
    if scn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")
    if scn.deleted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Scenario is not deleted")
    require_can_modify(scn, actor)
    scn.deleted_at = None
    scn.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="scenario",
        entity_id=scn.public_id,
        summary=f"Restored scenario '{scn.name}'",
        request_id=request_id,
    )
    return scn


def list_deleted_scenarios(db: Session) -> list[Scenario]:
    stmt = (
        select(Scenario)
        .where(Scenario.deleted_at.is_not(None))
        .order_by(Scenario.updated_at.desc())
    )
    return list(db.exec(stmt).all())


def transfer_ownership(
    db: Session,
    public_id: str,
    *,
    new_owner_user_id: int,
    actor: User,
    request_id: str | None = None,
) -> Scenario:
    """Reassign a scenario's owner. Owner-or-Approver+ only (H2)."""
    scn = get_scenario(db, public_id)
    require_can_modify(scn, actor)
    new_owner = db.get(User, new_owner_user_id)
    if new_owner is None or not new_owner.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Target user not found or inactive")
    prev = scn.owner_user_id
    scn.owner_user_id = new_owner_user_id
    scn.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.UPDATE,
        entity_type="scenario",
        entity_id=scn.public_id,
        summary=f"Transferred ownership of '{scn.name}' to {new_owner.email}",
        before={"owner_user_id": prev},
        after={"owner_user_id": new_owner_user_id},
        request_id=request_id,
    )
    return scn


def clone_scenario(
    db: Session, public_id: str, *, actor: User, request_id: str | None = None
) -> Scenario:
    src = get_scenario(db, public_id)
    payload = {
        col: getattr(src, col)
        for col in (
            "name",
            "description",
            "business_unit",
            "scenario_type",
            "tags",
            "owner_label",
            "mode",
            "inputs",
            "tolerance",
            "reduction_pct",
            "reference_lines",
            "prefs",
            "version_label",
            "assessment_date",
            "review_date",
            "threat_refs",
            "control_refs",
            "notes",
        )
    }
    payload["name"] = f"{src.name} (copy)"
    clone = Scenario(public_id=scenario_id(), owner_user_id=actor.id, **payload)
    db.add(clone)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.CREATE,
        entity_type="scenario",
        entity_id=clone.public_id,
        summary=f"Cloned '{src.name}' to '{clone.name}'",
        request_id=request_id,
    )
    return clone


def _to_read(scn: Scenario) -> dict[str, Any]:
    return {
        "id": scn.public_id,
        "name": scn.name,
        "description": scn.description,
        "business_unit": scn.business_unit,
        "scenario_type": scn.scenario_type,
        "tags": list(scn.tags or []),
        "owner_label": scn.owner_label,
        "owner_user_id": scn.owner_user_id,
        "mode": scn.mode,
        "inputs": scn.inputs,
        "tolerance": scn.tolerance,
        "reduction_pct": scn.reduction_pct,
        "reference_lines": scn.reference_lines or [],
        "prefs": scn.prefs or {},
        "version_label": scn.version_label,
        "assessment_date": scn.assessment_date,
        "review_date": scn.review_date,
        "approval_state": scn.approval_state,
        "threat_refs": scn.threat_refs or [],
        "control_refs": scn.control_refs or [],
        "notes": scn.notes,
        "created_at": scn.created_at,
        "updated_at": scn.updated_at,
        "latest_simulation_id": None,
    }
