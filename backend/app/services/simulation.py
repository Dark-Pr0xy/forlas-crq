"""Run-and-persist orchestration around the engine."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.config import settings
from app.engine import ENGINE_VERSION, RunResult, run_simulation
from app.engine.simulation import RunOptions
from app.models._base import AuditAction, SimulationStatus, utcnow
from app.models.scenario import Scenario
from app.models.settings import AppSettings
from app.models.simulation import SimulationArtifact, SimulationRun
from app.models.user import User
from app.services import audit
from app.services.ids import simulation_id

# Keep at most this many completed runs (with their heavy artifacts) per
# scenario. Older runs are pruned on each new completion so the DB doesn't grow
# without bound.
ARTIFACT_RETENTION_PER_SCENARIO = 5


def _resolve_options(
    db: Session, requested_iterations: int | None, requested_seed: int | None
) -> tuple[int, int]:
    settings_row = db.get(AppSettings, 1)
    iterations = requested_iterations or (settings_row.iterations if settings_row else 100_000)
    seed = requested_seed if requested_seed is not None else (
        settings_row.seed if settings_row else 42
    )
    return int(iterations), int(seed)


def run_for_scenario(
    db: Session,
    scenario: Scenario,
    *,
    iterations: int | None = None,
    seed: int | None = None,
    persist_artifacts: bool = True,
    actor: User | None = None,
    request_id: str | None = None,
) -> tuple[SimulationRun, RunResult]:
    """Execute a simulation synchronously and persist the result.

    The engine is vectorised NumPy; a 100k-iteration run completes in <300ms
    and the 1M ceiling in a couple of seconds. Anything above the ceiling is
    rejected rather than allowed to tie up a worker.
    """
    iters, seed_val = _resolve_options(db, iterations, seed)
    if iters > settings.sync_iteration_ceiling:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Requested {iters:,} iterations exceeds the maximum of "
            f"{settings.sync_iteration_ceiling:,}.",
        )

    run = SimulationRun(
        public_id=simulation_id(),
        scenario_id=scenario.id,
        triggered_by_user_id=actor.id if actor else None,
        iterations=iters,
        seed=seed_val,
        status=SimulationStatus.RUNNING,
        started_at=utcnow(),
        progress=0.0,
        inputs_at_run=dict(scenario.inputs or {}),
        mode_at_run=str(scenario.mode),
        engine_version=ENGINE_VERSION,
    )
    db.add(run)
    db.flush()

    try:
        result = run_simulation(
            {
                "mode": scenario.mode,
                "inputs": scenario.inputs,
                "tolerance": scenario.tolerance,
                "reduction_pct": scenario.reduction_pct,
            },
            RunOptions(iterations=iters, seed=seed_val),
        )
    except Exception as exc:
        run.status = SimulationStatus.FAILED
        run.error_message = str(exc)[:4000]
        run.completed_at = utcnow()
        db.flush()
        db.commit()
        raise

    _apply_result_to_run(run, result, scenario.tolerance or 0.0)
    if persist_artifacts:
        db.add(
            SimulationArtifact(
                simulation_run_id=run.id,
                losses=result.losses.astype(float).tolist(),
                sorted_losses=result.sorted_losses.astype(float).tolist(),
                lefs=result.lefs.astype(float).tolist(),
                histogram=result.histogram,
                lec_curve=result.lec_curve,
                driver_samples=result.driver_samples,
            )
        )
    db.flush()
    _prune_old_runs(db, scenario.id, keep=ARTIFACT_RETENTION_PER_SCENARIO)
    _invalidate_rollup_cache()
    audit.record(
        db,
        actor=actor,
        action=AuditAction.SIMULATE,
        entity_type="scenario",
        entity_id=scenario.public_id,
        summary=(
            f"Simulated '{scenario.name}' "
            f"({iters:,} iters, seed={seed_val}, ALE={result.mean:,.0f})"
        ),
        after={
            "simulation_id": run.public_id,
            "mean": result.mean,
            "p95": result.p95,
            "p99": result.p99,
        },
        request_id=request_id,
    )
    return run, result


def _apply_result_to_run(run: SimulationRun, result: RunResult, tolerance: float) -> None:
    run.status = SimulationStatus.COMPLETED
    run.progress = 1.0
    run.completed_at = utcnow()
    run.mean = result.mean
    run.std = result.std
    run.p5 = result.p5
    run.p25 = result.p25
    run.p50 = result.p50
    run.p75 = result.p75
    run.p90 = result.p90
    run.p95 = result.p95
    run.p99 = result.p99
    run.ci_lo = result.ci_lo
    run.ci_hi = result.ci_hi
    run.tail_mean = result.tail_mean
    run.zero_count = result.zero_count
    run.prob_exceed_tolerance = result.prob_exceed_tolerance
    run.tolerance_at_run = tolerance
    run.sensitivity = result.sensitivity


def _prune_old_runs(db: Session, scenario_id: int, *, keep: int) -> int:
    """Delete completed runs (and their artifacts) beyond the newest `keep`.

    Keeps the DB bounded — without this, every re-run left a multi-MB artifact
    behind forever.
    """
    runs = db.exec(
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario_id)
        .where(SimulationRun.status == SimulationStatus.COMPLETED)
        .order_by(SimulationRun.completed_at.desc())
    ).all()
    stale = runs[keep:]
    removed = 0
    for old in stale:
        artifact = db.get(SimulationArtifact, old.id)
        if artifact is not None:
            db.delete(artifact)
        db.delete(old)
        removed += 1
    if removed:
        db.flush()
    return removed


def get_latest_run(db: Session, scenario_id: int) -> SimulationRun | None:
    stmt = (
        select(SimulationRun)
        .where(SimulationRun.scenario_id == scenario_id)
        .where(SimulationRun.status == SimulationStatus.COMPLETED)
        .order_by(SimulationRun.completed_at.desc())
        .limit(1)
    )
    return db.exec(stmt).first()


# ---------------------------------------------------------------- rollup cache

# Small in-process cache for the portfolio rollup. Keyed on the tuple of latest
# completed-run ids across scenarios, so it invalidates automatically whenever a
# new run lands (the key changes) — plus explicit invalidation on run/snapshot.
_rollup_cache: dict[str, Any] = {"key": None, "value": None}


def _invalidate_rollup_cache() -> None:
    _rollup_cache["key"] = None
    _rollup_cache["value"] = None


def rollup_cache_get(key: str) -> Any | None:
    if _rollup_cache["key"] == key:
        return _rollup_cache["value"]
    return None


def rollup_cache_set(key: str, value: Any) -> None:
    _rollup_cache["key"] = key
    _rollup_cache["value"] = value


def get_artifact(db: Session, run_id: int) -> SimulationArtifact | None:
    return db.get(SimulationArtifact, run_id)


def serialize_run(run: SimulationRun, *, with_artifact: SimulationArtifact | None) -> dict[str, Any]:
    """Render a run + (optional) artifact for the API."""
    base: dict[str, Any] = {
        "id": run.public_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "progress": run.progress,
        "iterations": run.iterations,
        "seed": run.seed,
        "engine_version": run.engine_version,
        "mode_at_run": run.mode_at_run,
        "inputs_at_run": run.inputs_at_run,
        "statistics": None,
        "sensitivity": run.sensitivity,
        "histogram": None,
        "lec_curve": None,
        "losses_url": None,
        "driver_samples_url": None,
    }
    if run.status == SimulationStatus.COMPLETED:
        base["statistics"] = {
            "mean": run.mean,
            "std": run.std,
            "p5": run.p5,
            "p25": run.p25,
            "p50": run.p50,
            "p75": run.p75,
            "p90": run.p90,
            "p95": run.p95,
            "p99": run.p99,
            "ci_lo": run.ci_lo,
            "ci_hi": run.ci_hi,
            "tail_mean": run.tail_mean,
            "zero_count": run.zero_count or 0,
            "iterations": run.iterations,
            "seed": run.seed,
            "prob_exceed_tolerance": run.prob_exceed_tolerance or 0.0,
            "tolerance": run.tolerance_at_run or 0.0,
            "tolerance_utilisation": (
                (run.mean / run.tolerance_at_run)
                if run.tolerance_at_run and run.tolerance_at_run > 0
                else 0.0
            ),
            "difference_to_tolerance": (
                (run.tolerance_at_run - run.mean)
                if run.tolerance_at_run is not None and run.mean is not None
                else 0.0
            ),
        }
    if with_artifact is not None:
        base["histogram"] = with_artifact.histogram
        base["lec_curve"] = with_artifact.lec_curve
        base["losses_url"] = f"/api/simulations/{run.public_id}/losses"
        base["driver_samples_url"] = f"/api/simulations/{run.public_id}/drivers"
    return base
