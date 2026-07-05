"""Simulation run endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.deps import CurrentUser, RequestId, ReviewerUser, SessionDep
from app.models.scenario import Scenario
from app.models.simulation import SimulationArtifact, SimulationRun
from app.schemas.simulation import SimulationRequest, SimulationResultFull
from app.services import scenario as scn_svc
from app.services import simulation as sim_svc

router = APIRouter(prefix="/api", tags=["simulations"])


@router.post(
    "/scenarios/{scenario_id}/simulations",
    response_model=SimulationResultFull,
    status_code=status.HTTP_201_CREATED,
)
def trigger_simulation(
    scenario_id: str,
    payload: SimulationRequest,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scenario = scn_svc.get_scenario(db, scenario_id)
    run, _ = sim_svc.run_for_scenario(
        db,
        scenario,
        iterations=payload.iterations,
        seed=payload.seed,
        persist_artifacts=payload.persist_artifacts,
        actor=user,
        request_id=request_id,
    )
    db.commit()
    artifact = sim_svc.get_artifact(db, run.id) if payload.persist_artifacts else None
    body = sim_svc.serialize_run(run, with_artifact=artifact)
    body["scenario_id"] = scenario.public_id
    return body


@router.get(
    "/scenarios/{scenario_id}/simulations/latest",
    response_model=SimulationResultFull,
)
def get_latest(scenario_id: str, db: SessionDep, _: CurrentUser):
    scenario = scn_svc.get_scenario(db, scenario_id)
    run = sim_svc.get_latest_run(db, scenario.id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No simulation runs yet")
    artifact = sim_svc.get_artifact(db, run.id)
    body = sim_svc.serialize_run(run, with_artifact=artifact)
    body["scenario_id"] = scenario.public_id
    return body


@router.get("/simulations/{run_id}/losses")
def get_losses(
    run_id: str,
    db: SessionDep,
    _: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(5000, ge=1, le=50_000),
):
    """Paginated slice of the raw loss vector (M7).

    Returns at most `limit` rows starting at `offset` plus a `total` count, so
    the UI table can page instead of pulling a multi-MB response at once.
    """
    run = db.exec(select(SimulationRun).where(SimulationRun.public_id == run_id)).first()
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    artifact = db.get(SimulationArtifact, run.id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact pruned")
    total = len(artifact.losses)
    end = min(offset + limit, total)
    return {
        "losses": artifact.losses[offset:end],
        "lefs": artifact.lefs[offset:end],
        "offset": offset,
        "limit": limit,
        "total": total,
    }


@router.get("/simulations/{run_id}/losses.csv")
def download_losses_csv(run_id: str, db: SessionDep, _: CurrentUser):
    """Stream the full loss vector as CSV so exports don't buffer a huge JSON
    response in memory or the browser tab (M7)."""
    from fastapi.responses import StreamingResponse

    run = db.exec(select(SimulationRun).where(SimulationRun.public_id == run_id)).first()
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    artifact = db.get(SimulationArtifact, run.id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact pruned")

    losses = artifact.losses
    lefs = artifact.lefs
    n = len(losses)
    n_lefs = len(lefs)

    def _rows():
        # Batch rows into large chunks. Yielding one line at a time forces an
        # ASGI send per row, which made a 100k-row export take seconds; joining
        # ~20k rows per chunk cuts that overhead by four orders of magnitude.
        yield "iteration,loss,lef\n"
        chunk = 20_000
        for start in range(0, n, chunk):
            end = min(start + chunk, n)
            buf = [
                f"{i + 1},{losses[i]:.2f},{(lefs[i] if i < n_lefs else 0.0):.6f}"
                for i in range(start, end)
            ]
            yield "\n".join(buf) + "\n"

    return StreamingResponse(
        _rows(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="simulation_{run_id}.csv"'},
    )


@router.get("/simulations/{run_id}/drivers")
def get_drivers(run_id: str, db: SessionDep, _: CurrentUser):
    run = db.exec(select(SimulationRun).where(SimulationRun.public_id == run_id)).first()
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    artifact = db.get(SimulationArtifact, run.id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact pruned")
    return artifact.driver_samples or {}
