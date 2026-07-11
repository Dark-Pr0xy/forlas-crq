"""Scenario CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.deps import CurrentUser, RequestId, ReviewerUser, SessionDep
from app.schemas.common import Message
from app.schemas.scenario import (
    ScenarioCreate,
    ScenarioRead,
    ScenarioUpdate,
)
from app.services import scenario as scn_svc

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioRead])
def list_scenarios(db: SessionDep, _: CurrentUser):
    return [ScenarioRead.model_validate(scn_svc._to_read(s)) for s in scn_svc.list_scenarios(db)]


@router.get("/deleted", response_model=list[ScenarioRead])
def list_deleted(db: SessionDep, _: CurrentUser):
    return [ScenarioRead.model_validate(scn_svc._to_read(s)) for s in scn_svc.list_deleted_scenarios(db)]


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreate, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    scn = scn_svc.create_scenario(db, payload, actor=user, request_id=request_id)
    db.commit()
    return ScenarioRead.model_validate(scn_svc._to_read(scn))


@router.get("/{public_id}", response_model=ScenarioRead)
def get_scenario(public_id: str, db: SessionDep, _: CurrentUser):
    scn = scn_svc.get_scenario(db, public_id)
    return ScenarioRead.model_validate(scn_svc._to_read(scn))


@router.patch("/{public_id}", response_model=ScenarioRead)
def update_scenario(
    public_id: str,
    payload: ScenarioUpdate,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scn = scn_svc.update_scenario(db, public_id, payload, actor=user, request_id=request_id)
    db.commit()
    return ScenarioRead.model_validate(scn_svc._to_read(scn))


@router.delete("/{public_id}", response_model=Message)
def delete_scenario(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    scn_svc.soft_delete_scenario(db, public_id, actor=user, request_id=request_id)
    db.commit()
    return Message(message="Deleted")


@router.post("/{public_id}/clone", response_model=ScenarioRead)
def clone_scenario(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    clone = scn_svc.clone_scenario(db, public_id, actor=user, request_id=request_id)
    db.commit()
    return ScenarioRead.model_validate(scn_svc._to_read(clone))


@router.post("/{public_id}/restore", response_model=ScenarioRead)
def restore_scenario(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    scn = scn_svc.restore_scenario(db, public_id, actor=user, request_id=request_id)
    db.commit()
    return ScenarioRead.model_validate(scn_svc._to_read(scn))


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: int


@router.post("/{public_id}/transfer-ownership", response_model=ScenarioRead)
def transfer_ownership(
    public_id: str,
    payload: TransferOwnershipRequest,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    scn = scn_svc.transfer_ownership(
        db,
        public_id,
        new_owner_user_id=payload.new_owner_user_id,
        actor=user,
        request_id=request_id,
    )
    db.commit()
    return ScenarioRead.model_validate(scn_svc._to_read(scn))
