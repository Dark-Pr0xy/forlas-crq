"""Analysis & evidence endpoints (per scenario)."""

from __future__ import annotations

from fastapi import APIRouter

from app.deps import CurrentUser, RequestId, ReviewerUser, SessionDep
from app.schemas.analysis import AnalysisRead, AnalysisUpdate
from app.services import analysis as analysis_svc
from app.services import scenario as scn_svc

router = APIRouter(prefix="/api/scenarios", tags=["analysis"])


@router.get("/{scenario_id}/analysis", response_model=AnalysisRead)
def get_analysis(scenario_id: str, db: SessionDep, _: CurrentUser) -> AnalysisRead:
    scn = scn_svc.get_scenario(db, scenario_id)
    return AnalysisRead.model_validate(analysis_svc.read_analysis(db, scn))


@router.put("/{scenario_id}/analysis", response_model=AnalysisRead)
def put_analysis(
    scenario_id: str,
    payload: AnalysisUpdate,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
) -> AnalysisRead:
    scn = scn_svc.get_scenario(db, scenario_id)
    data = analysis_svc.upsert_analysis(db, scn, payload, actor=user, request_id=request_id)
    db.commit()
    return AnalysisRead.model_validate(data)
