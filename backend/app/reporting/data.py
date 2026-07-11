"""Assemble the data dictionary the report templates consume.

A single shape covers Executive and Board reports; the templates pick the
sections they want.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.config import settings
from app.engine.portfolio import aggregate
from app.models._base import SimulationStatus
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun
from app.services.portfolio import collect_latest_runs


def _scenario_context(db: Session, scenarios: list[Scenario]) -> list[dict[str, Any]]:
    out = []
    for scn in scenarios:
        run = db.exec(
            select(SimulationRun)
            .where(SimulationRun.scenario_id == scn.id)
            .where(SimulationRun.status == SimulationStatus.COMPLETED)
            .order_by(SimulationRun.completed_at.desc())
            .limit(1)
        ).first()
        sens = run.sensitivity if run else None
        out.append(
            {
                "id": scn.public_id,
                "name": scn.name,
                "business_unit": scn.business_unit,
                "owner": scn.owner_label,
                "scenario_type": scn.scenario_type,
                "tolerance": scn.tolerance or 0,
                "tags": list(scn.tags or []),
                "mode": str(scn.mode),
                "version": scn.version_label,
                "review_date": scn.review_date,
                "assessment_date": scn.assessment_date,
                "notes": scn.notes,
                "simulated": run is not None,
                "ale": run.mean if run else None,
                "p50": run.p50 if run else None,
                "p90": run.p90 if run else None,
                "p95": run.p95 if run else None,
                "p99": run.p99 if run else None,
                "tail_mean": run.tail_mean if run else None,
                "prob_exceed_tolerance": run.prob_exceed_tolerance if run else None,
                "ci_lo": run.ci_lo if run else None,
                "ci_hi": run.ci_hi if run else None,
                "iterations": run.iterations if run else None,
                "seed": run.seed if run else None,
                "std": run.std if run else None,
                "last_simulated_at": run.completed_at if run else None,
                "sensitivity": sens,
                "inputs_at_run": (run.inputs_at_run if run else None) or scn.inputs,
                "threat_refs": list(scn.threat_refs or []),
                "control_refs": list(scn.control_refs or []),
            }
        )
    return out


def build_report_context(
    db: Session,
    *,
    scenarios: list[Scenario],
    appetite: float | None = None,
    title: str | None = None,
    kind: str = "executive",
) -> dict[str, Any]:
    inputs = collect_latest_runs(db, scenarios)
    rollup = aggregate(inputs)
    return {
        "title": title or ("Executive Summary" if kind == "executive" else "Board Pack"),
        "kind": kind,
        "generated_at": datetime.utcnow(),
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "scenarios": _scenario_context(db, scenarios),
        "scenario_count": len(scenarios),
        "simulated_count": len(inputs),
        "portfolio": {
            "total_ale": rollup.total_ale,
            "total_p50": rollup.total_p50,
            "total_p90": rollup.total_p90,
            "total_p95": rollup.total_p95,
            "total_p99": rollup.total_p99,
            "total_tail": rollup.total_tail,
            "ci_lo": rollup.ci_lo,
            "ci_hi": rollup.ci_hi,
            "over_tolerance_count": rollup.over_tolerance_count,
            "iterations": rollup.iterations,
            "per_scenario": rollup.per_scenario,
            "appetite": appetite,
            "appetite_utilisation": (
                rollup.total_ale / appetite if appetite and appetite > 0 else None
            ),
        },
    }
