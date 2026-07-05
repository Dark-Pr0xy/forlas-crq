"""Portfolio orchestration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from sqlmodel import Session, select

from app.engine.portfolio import (
    PortfolioInput,
    PortfolioRollupResult,
    aggregate,
)
from app.models._base import AuditAction, SimulationStatus
from app.models.portfolio import PortfolioSnapshot
from app.models.scenario import Scenario
from app.models.simulation import SimulationArtifact, SimulationRun
from app.models.user import User
from app.services import audit


def collect_latest_runs(db: Session, scenarios: list[Scenario]) -> list[PortfolioInput]:
    """Fetch each scenario's most recent completed run + artifact and turn it
    into a `PortfolioInput`. Scenarios without a completed run are skipped."""

    out: list[PortfolioInput] = []
    for scn in scenarios:
        run = db.exec(
            select(SimulationRun)
            .where(SimulationRun.scenario_id == scn.id)
            .where(SimulationRun.status == SimulationStatus.COMPLETED)
            .order_by(SimulationRun.completed_at.desc())
            .limit(1)
        ).first()
        if run is None:
            continue
        artifact = db.get(SimulationArtifact, run.id)
        if artifact is None or not artifact.losses:
            continue
        out.append(
            PortfolioInput(
                scenario_public_id=scn.public_id,
                scenario_name=scn.name,
                tolerance=float(scn.tolerance or 0.0),
                losses=np.asarray(artifact.losses, dtype=np.float64),
            )
        )
    return out


def latest_run_signature(db: Session, scenarios: list[Scenario]) -> str:
    """A stable key over each scenario's latest completed run id.

    Feeds the rollup cache: the moment a new run completes for any scenario the
    signature changes, so a cached rollup is never served stale.
    """
    parts: list[str] = []
    for scn in scenarios:
        run = db.exec(
            select(SimulationRun.public_id)
            .where(SimulationRun.scenario_id == scn.id)
            .where(SimulationRun.status == SimulationStatus.COMPLETED)
            .order_by(SimulationRun.completed_at.desc())
            .limit(1)
        ).first()
        if run is not None:
            parts.append(f"{scn.public_id}:{run}")
    return "|".join(sorted(parts))


def rollup_for_scenarios(
    db: Session,
    scenarios: list[Scenario],
    *,
    appetite: float | None = None,
    insurance_deductible: float = 0.0,
    insurance_limit: float | None = None,
) -> tuple[PortfolioRollupResult, int]:
    """Returns (rollup, simulated_count).

    `appetite` is not passed to `aggregate` — appetite utilisation is computed
    in `serialize_rollup`, so the engine function doesn't need it (M4).
    """
    inputs = collect_latest_runs(db, scenarios)
    rollup = aggregate(
        inputs,
        insurance_deductible=insurance_deductible,
        insurance_limit=insurance_limit,
    )
    return rollup, len(inputs)


def take_snapshot(
    db: Session,
    *,
    rollup: PortfolioRollupResult,
    scenario_count: int,
    simulated_count: int,
    reason: str,
    actor: User | None,
    portfolio_id: int | None = None,
    request_id: str | None = None,
) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(
        portfolio_id=portfolio_id,
        captured_by_user_id=actor.id if actor else None,
        total_ale=rollup.total_ale,
        total_p50=rollup.total_p50,
        total_p90=rollup.total_p90,
        total_p95=rollup.total_p95,
        total_p99=rollup.total_p99,
        scenario_count=scenario_count,
        simulated_count=simulated_count,
        reason=reason,
    )
    db.add(snap)
    db.flush()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.SNAPSHOT,
        entity_type="portfolio",
        entity_id=str(portfolio_id) if portfolio_id else "default",
        summary=f"Captured snapshot · {reason} · ALE {rollup.total_ale:,.0f}",
        after={
            "total_ale": rollup.total_ale,
            "total_p95": rollup.total_p95,
            "total_p99": rollup.total_p99,
            "scenario_count": scenario_count,
            "simulated_count": simulated_count,
        },
        request_id=request_id,
    )
    return snap


def serialize_rollup(
    rollup: PortfolioRollupResult,
    *,
    simulated_count: int,
    appetite: float | None,
) -> dict[str, Any]:
    return {
        "portfolio_id": None,
        "scenario_count": rollup.scenario_count,
        "simulated_count": simulated_count,
        "iterations": rollup.iterations,
        "total_ale": rollup.total_ale,
        "total_p50": rollup.total_p50,
        "total_p90": rollup.total_p90,
        "total_p95": rollup.total_p95,
        "total_p99": rollup.total_p99,
        "total_tail": rollup.total_tail,
        "ci_lo": rollup.ci_lo,
        "ci_hi": rollup.ci_hi,
        "over_tolerance_count": rollup.over_tolerance_count,
        "appetite": appetite,
        "appetite_utilisation": (
            rollup.total_ale / appetite if appetite and appetite > 0 else None
        ),
        "histogram": rollup.histogram,
        "lec_curve": rollup.lec_curve,
        "top_scenarios": rollup.per_scenario[:10],
    }
