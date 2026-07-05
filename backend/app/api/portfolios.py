"""Portfolio endpoints.

Phase 4 ships the default portfolio rollup, snapshots, and the register view.
Named portfolio CRUD lands later if needed — for now the only portfolio is
"all active scenarios".
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlmodel import select

from app.deps import CurrentUser, RequestId, ReviewerUser, SessionDep
from app.models._base import SimulationStatus
from app.models.portfolio import PortfolioSnapshot
from app.models.scenario import Scenario
from app.models.simulation import SimulationRun
from app.schemas.common import Message
from app.services import portfolio as portfolio_svc
from app.services import scenario as scn_svc

router = APIRouter(prefix="/api/portfolio", tags=["portfolios"])


class PortfolioRollup(BaseModel):
    portfolio_id: str | None
    scenario_count: int
    simulated_count: int
    iterations: int
    total_ale: float
    total_p50: float
    total_p90: float
    total_p95: float
    total_p99: float
    total_tail: float
    ci_lo: float
    ci_hi: float
    over_tolerance_count: int
    appetite: float | None
    appetite_utilisation: float | None
    histogram: dict[str, Any]
    lec_curve: list[list[float]]
    top_scenarios: list[dict[str, Any]]


class SnapshotRequest(BaseModel):
    reason: str = "manual"
    appetite: float | None = None


class SnapshotEntry(BaseModel):
    id: int
    created_at: datetime
    total_ale: float
    total_p95: float
    total_p99: float
    scenario_count: int
    simulated_count: int
    reason: str


@router.get("/rollup", response_model=PortfolioRollup)
def get_default_rollup(
    db: SessionDep,
    _: CurrentUser,
    appetite: float | None = Query(default=None),
    insurance_deductible: float = Query(default=0.0, ge=0),
    insurance_limit: float | None = Query(default=None),
    scenario_ids: list[str] | None = Query(default=None),
):
    from app.services import simulation as sim_svc

    scenarios = scn_svc.list_scenarios(db)
    # Optional subset (M1): presentation mode + reports filter to selected ids.
    if scenario_ids:
        wanted = set(scenario_ids)
        scenarios = [s for s in scenarios if s.public_id in wanted]
    # Cache on the latest-run signature + params so the hot dashboard path
    # doesn't re-parse every loss vector on each poll.
    signature = portfolio_svc.latest_run_signature(db, scenarios)
    cache_key = f"{signature}#a={appetite}#d={insurance_deductible}#l={insurance_limit}"
    cached = sim_svc.rollup_cache_get(cache_key)
    if cached is not None:
        return cached

    rollup, sim_count = portfolio_svc.rollup_for_scenarios(
        db,
        scenarios,
        appetite=appetite,
        insurance_deductible=insurance_deductible,
        insurance_limit=insurance_limit,
    )
    payload = portfolio_svc.serialize_rollup(rollup, simulated_count=sim_count, appetite=appetite)
    sim_svc.rollup_cache_set(cache_key, payload)
    return payload


@router.post("/snapshots", response_model=SnapshotEntry, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    payload: SnapshotRequest,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scenarios = scn_svc.list_scenarios(db)
    rollup, sim_count = portfolio_svc.rollup_for_scenarios(
        db,
        scenarios,
        appetite=payload.appetite,
    )
    snap = portfolio_svc.take_snapshot(
        db,
        rollup=rollup,
        scenario_count=len(scenarios),
        simulated_count=sim_count,
        reason=payload.reason,
        actor=user,
        request_id=request_id,
    )
    db.commit()
    return SnapshotEntry.model_validate(snap, from_attributes=True)


@router.get("/snapshots", response_model=list[SnapshotEntry])
def list_snapshots(
    db: SessionDep, _: CurrentUser, limit: int = Query(50, ge=1, le=500)
):
    rows = db.exec(
        select(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.created_at.desc())
        .limit(limit)
    ).all()
    return [SnapshotEntry.model_validate(r, from_attributes=True) for r in rows]


# ----------------------------------------------------------------- register


class RegisterRow(BaseModel):
    scenario_id: str
    name: str
    business_unit: str | None
    owner_label: str | None
    tags: list[str]
    mode: str
    ale: float | None
    p50: float | None
    p95: float | None
    p99: float | None
    tail_mean: float | None
    tolerance: float
    utilisation: float | None
    prob_exceed_tolerance: float | None
    over_tolerance: bool
    last_simulated_at: datetime | None
    version_label: str
    review_date: str | None


@router.get("/register", response_model=list[RegisterRow])
def get_register(db: SessionDep, _: CurrentUser):
    """Denormalised exposure-register view."""
    scenarios = scn_svc.list_scenarios(db)
    rows: list[RegisterRow] = []
    for scn in scenarios:
        run = db.exec(
            select(SimulationRun)
            .where(SimulationRun.scenario_id == scn.id)
            .where(SimulationRun.status == SimulationStatus.COMPLETED)
            .order_by(SimulationRun.completed_at.desc())
            .limit(1)
        ).first()
        utilisation = None
        over = False
        if run and run.mean is not None and scn.tolerance and scn.tolerance > 0:
            utilisation = run.mean / scn.tolerance
            over = run.mean > scn.tolerance
        rows.append(
            RegisterRow(
                scenario_id=scn.public_id,
                name=scn.name,
                business_unit=scn.business_unit,
                owner_label=scn.owner_label,
                tags=list(scn.tags or []),
                mode=str(scn.mode),
                ale=run.mean if run else None,
                p50=run.p50 if run else None,
                p95=run.p95 if run else None,
                p99=run.p99 if run else None,
                tail_mean=run.tail_mean if run else None,
                tolerance=scn.tolerance or 0,
                utilisation=utilisation,
                prob_exceed_tolerance=run.prob_exceed_tolerance if run else None,
                over_tolerance=over,
                last_simulated_at=run.completed_at if run else None,
                version_label=scn.version_label,
                review_date=scn.review_date,
            )
        )
    return rows
