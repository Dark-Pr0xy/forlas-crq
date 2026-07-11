"""System endpoints: health, ULA acknowledgement, settings."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, UploadFile, status
from pydantic import BaseModel
from sqlmodel import select

from app.config import settings
from app.deps import CurrentUser, OwnerUser, RequestId, ReviewerUser, SessionDep
from app.models._base import AuditAction, utcnow
from app.models.settings import AppSettings
from app.schemas.common import Message
from app.services import approvals as approval_svc
from app.services import audit
from app.services import scenario as scn_svc
from app.services.import_alpha import import_alpha_payload
from app.services.seed import ensure_app_settings

ULA_VERSION = "1.0"

router = APIRouter(prefix="/api", tags=["system"])


class HealthResponse(BaseModel):
    name: str
    version: str
    status: str
    database: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
def health(db: SessionDep) -> HealthResponse:
    db.exec(select(AppSettings).limit(1)).first()
    return HealthResponse(
        name=settings.app_name,
        version=settings.app_version,
        status="ok",
        database=settings.database_path.as_posix(),
        timestamp=utcnow(),
    )


class UlaAcknowledge(BaseModel):
    version: str = ULA_VERSION


@router.post("/ula/acknowledge", response_model=Message)
def acknowledge_ula(
    payload: UlaAcknowledge,
    db: SessionDep,
    user: CurrentUser,
    request_id: RequestId,
) -> Message:
    s = ensure_app_settings(db)
    s.ula_acknowledged_version = payload.version
    s.ula_acknowledged_at = utcnow()
    s.ula_acknowledged_by_user_id = user.id
    s.updated_at = utcnow()
    audit.record(
        db,
        actor=user,
        action=AuditAction.UPDATE,
        entity_type="ula",
        entity_id=payload.version,
        summary=f"Acknowledged ULA v{payload.version}",
        request_id=request_id,
    )
    db.commit()
    return Message(message=f"ULA v{payload.version} acknowledged")


class SettingsRead(BaseModel):
    iterations: int
    seed: int
    theme: str
    ula_acknowledged_version: str | None
    ula_acknowledged_at: datetime | None
    enforce_separation_of_duties: bool
    scenario_types: list[str]


class SettingsUpdate(BaseModel):
    iterations: int | None = None
    seed: int | None = None
    theme: str | None = None
    enforce_separation_of_duties: bool | None = None


def _settings_read(db: SessionDep, s: AppSettings) -> SettingsRead:
    return SettingsRead(
        iterations=s.iterations,
        seed=s.seed,
        theme=s.theme,
        ula_acknowledged_version=s.ula_acknowledged_version,
        ula_acknowledged_at=s.ula_acknowledged_at,
        enforce_separation_of_duties=approval_svc.separation_of_duties_enabled(db),
        scenario_types=scn_svc.list_scenario_types(db),
    )


@router.get("/settings", response_model=SettingsRead)
def get_settings(db: SessionDep, _: CurrentUser) -> SettingsRead:
    s = ensure_app_settings(db)
    return _settings_read(db, s)


@router.patch("/settings", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate, db: SessionDep, user: OwnerUser, request_id: RequestId
) -> SettingsRead:
    s = ensure_app_settings(db)
    data = payload.model_dump(exclude_unset=True)
    sod = data.pop("enforce_separation_of_duties", None)
    for k, v in data.items():
        setattr(s, k, v)
    if sod is not None:
        extras = dict(s.extras or {})
        extras["enforce_separation_of_duties"] = bool(sod)
        s.extras = extras  # reassign so the JSON column change is tracked
    s.updated_at = utcnow()
    audit.record(
        db,
        actor=user,
        action=AuditAction.UPDATE,
        entity_type="settings",
        entity_id="app",
        summary="Updated application settings",
        after=payload.model_dump(exclude_unset=True),
        request_id=request_id,
    )
    db.commit()
    return _settings_read(db, s)


# ------------------------------------------------------------- scenario types


class ScenarioTypesRead(BaseModel):
    types: list[str]


class ScenarioTypeCreate(BaseModel):
    name: str


@router.get("/scenario-types", response_model=ScenarioTypesRead)
def list_scenario_types(db: SessionDep, _: CurrentUser) -> ScenarioTypesRead:
    return ScenarioTypesRead(types=scn_svc.list_scenario_types(db))


@router.post(
    "/scenario-types",
    response_model=ScenarioTypesRead,
    status_code=status.HTTP_201_CREATED,
)
def add_scenario_type(
    payload: ScenarioTypeCreate,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
) -> ScenarioTypesRead:
    types, added = scn_svc.add_scenario_type(db, payload.name)
    if added:
        # Duplicates are a harmless no-op — don't fabricate an audit entry.
        audit.record(
            db,
            actor=user,
            action=AuditAction.CREATE,
            entity_type="scenario_type",
            entity_id=payload.name.strip(),
            summary=f"Added scenario type '{payload.name.strip()}'",
            request_id=request_id,
        )
    db.commit()
    return ScenarioTypesRead(types=types)


@router.post(
    "/import/alpha",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def import_alpha(
    file: UploadFile,
    db: SessionDep,
    owner: OwnerUser,
    request_id: RequestId,
) -> Message:
    import json

    body = await file.read()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        from fastapi import HTTPException

        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid JSON: {exc.msg}") from exc
    result = import_alpha_payload(db, payload, owner=owner)
    audit.record(
        db,
        actor=owner,
        action=AuditAction.IMPORT,
        entity_type="scenario",
        entity_id=None,
        summary=(
            f"Imported {result.inserted} scenario(s) from Alpha JSON"
            + (f", skipped {result.skipped} invalid" if result.skipped else "")
        ),
        request_id=request_id,
    )
    db.commit()
    message = f"Imported {result.inserted} scenario(s) from Alpha export"
    if result.skipped:
        message += f" · skipped {result.skipped} with invalid inputs"
    return Message(message=message)


# ----------------------------------------------------------------- backup


@router.post("/backup", response_model=Message, status_code=status.HTTP_201_CREATED)
def create_backup(
    db: SessionDep,
    owner: OwnerUser,
    request_id: RequestId,
) -> Message:
    """Manual on-demand backup via SQLite's online-backup API (safe while serving)."""
    from app.db import get_engine
    from app.services import backup as backup_svc

    target = backup_svc.take_backup(get_engine(), settings.backups_dir, prefix="manual")
    audit.record(
        db,
        actor=owner,
        action=AuditAction.EXPORT,
        entity_type="backup",
        entity_id=target.name,
        summary=f"Created backup {target.name}",
        request_id=request_id,
    )
    db.commit()
    return Message(message=f"Backup written: {target}")


class BackupEntry(BaseModel):
    filename: str
    size_bytes: int
    created_at: datetime


@router.get("/backups", response_model=list[BackupEntry])
def list_backups(_: CurrentUser) -> list[BackupEntry]:
    if not settings.backups_dir.exists():
        return []
    out = []
    for p in sorted(
        settings.backups_dir.glob("*.db"), key=lambda x: x.stat().st_mtime, reverse=True
    ):
        st = p.stat()
        out.append(
            BackupEntry(
                filename=p.name,
                size_bytes=st.st_size,
                created_at=datetime.fromtimestamp(st.st_mtime),
            )
        )
    return out
