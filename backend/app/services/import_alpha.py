"""Import scenarios from an Alpha (single-file HTML) export.

The Alpha's `exportAll` produces the raw localStorage payload (`KEY =
'forlas.fairCrq.v1'`). We accept that shape and map it onto the new model
so users can pick up where they left off.

Imported scenarios are validated against the engine's required-inputs rules;
anything that couldn't be simulated is skipped rather than stored as an
unusable row (which would 500 the first time someone hit "Run").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.engine.errors import SimulationInputError, validate_inputs
from app.models._base import DecompositionMode
from app.models.scenario import Scenario
from app.models.user import User
from app.services.ids import scenario_id


@dataclass
class ImportResult:
    inserted: int
    skipped: int
    skipped_names: list[str]


def import_alpha_payload(db: Session, payload: dict[str, Any], *, owner: User) -> ImportResult:
    raw_scenarios = payload.get("scenarios") or []
    inserted = 0
    skipped = 0
    skipped_names: list[str] = []
    for raw in raw_scenarios:
        name = (raw or {}).get("name") if isinstance(raw, dict) else None
        try:
            scn = _map_scenario(raw, owner)
            # Reject anything the engine couldn't run — surfaced as a count.
            # Pass the enum member; validate_inputs coerces via `.value`.
            validate_inputs(scn.mode, scn.inputs)
        except (SimulationInputError, ValueError, TypeError, AttributeError):
            skipped += 1
            if name:
                skipped_names.append(str(name))
            continue
        db.add(scn)
        inserted += 1
    db.flush()
    return ImportResult(inserted=inserted, skipped=skipped, skipped_names=skipped_names)


def _map_scenario(raw: dict[str, Any], owner: User) -> Scenario:
    if not isinstance(raw, dict):
        raise TypeError("scenario entry is not an object")
    mode_raw = raw.get("mode") or "tef-vuln"
    mode = (
        DecompositionMode(mode_raw)
        if mode_raw in DecompositionMode._value2member_map_
        else DecompositionMode.TEF_VULN
    )
    return Scenario(
        public_id=scenario_id(),
        owner_user_id=owner.id,
        owner_label=raw.get("owner"),
        name=raw.get("name") or "Imported scenario",
        business_unit=raw.get("bu"),
        scenario_type=raw.get("type"),
        tags=list(raw.get("tags") or []),
        mode=mode,
        inputs=dict(raw.get("inputs") or {}),
        tolerance=float(raw.get("tolerance") or 0),
        reduction_pct=float(raw.get("reductionPct") or 0),
        reference_lines=list(raw.get("refLines") or []),
        prefs=dict(raw.get("prefs") or {}),
        version_label=str(raw.get("version") or "1.0"),
        assessment_date=raw.get("assessmentDate"),
        review_date=raw.get("reviewDate"),
        notes=raw.get("notes"),
    )
