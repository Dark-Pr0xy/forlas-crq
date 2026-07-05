"""Knowledge library endpoints — threats, controls, benchmarks + import."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlmodel import select

from app.deps import CurrentUser, OwnerUser, RequestId, ReviewerUser, SessionDep
from app.models._base import AuditAction, utcnow
from app.models.knowledge import BenchmarkEntry, ControlEntry, ThreatEntry
from app.schemas.common import Message
from app.services import audit

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _short_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(6)}"


class ThreatRead(BaseModel):
    id: str
    name: str
    category: str | None
    source: str
    description: str | None
    references: list[str]
    attributes: dict[str, Any] | None = None


class ControlRead(BaseModel):
    id: str
    framework: str
    code: str
    name: str
    description: str | None
    category: str | None
    source: str
    attributes: dict[str, Any] | None = None


class BenchmarkRead(BaseModel):
    id: str
    name: str
    industry: str | None
    metric: str
    distribution: dict[str, Any]
    citation: str | None
    source: str


def _t(row: ThreatEntry) -> ThreatRead:
    return ThreatRead(
        id=row.public_id,
        name=row.name,
        category=row.category,
        source=row.source,
        description=row.description,
        references=list(row.references or []),
        attributes=row.attributes,
    )


def _c(row: ControlEntry) -> ControlRead:
    return ControlRead(
        id=row.public_id,
        framework=row.framework,
        code=row.code,
        name=row.name,
        description=row.description,
        category=row.category,
        source=row.source,
        attributes=row.attributes,
    )


def _b(row: BenchmarkEntry) -> BenchmarkRead:
    return BenchmarkRead(
        id=row.public_id,
        name=row.name,
        industry=row.industry,
        metric=row.metric,
        distribution=row.distribution,
        citation=row.citation,
        source=row.source,
    )


# -------------------------------------------------------------- list endpoints


@router.get("/threats", response_model=list[ThreatRead])
def list_threats(
    db: SessionDep,
    _: CurrentUser,
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    stmt = select(ThreatEntry).order_by(ThreatEntry.category, ThreatEntry.name)
    if category:
        stmt = stmt.where(ThreatEntry.category == category)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(ThreatEntry.name.ilike(like))
    return [_t(r) for r in db.exec(stmt).all()]


@router.get("/controls", response_model=list[ControlRead])
def list_controls(
    db: SessionDep,
    _: CurrentUser,
    q: str | None = Query(default=None),
    framework: str | None = Query(default=None),
):
    stmt = select(ControlEntry).order_by(ControlEntry.framework, ControlEntry.code)
    if framework:
        stmt = stmt.where(ControlEntry.framework == framework)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(ControlEntry.name.ilike(like))
    return [_c(r) for r in db.exec(stmt).all()]


@router.get("/benchmarks", response_model=list[BenchmarkRead])
def list_benchmarks(
    db: SessionDep,
    _: CurrentUser,
    q: str | None = Query(default=None),
    industry: str | None = Query(default=None),
    metric: str | None = Query(default=None),
):
    stmt = select(BenchmarkEntry).order_by(BenchmarkEntry.industry, BenchmarkEntry.name)
    if industry:
        stmt = stmt.where(BenchmarkEntry.industry == industry)
    if metric:
        stmt = stmt.where(BenchmarkEntry.metric == metric)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(BenchmarkEntry.name.ilike(like))
    return [_b(r) for r in db.exec(stmt).all()]


# -------------------------------------------------------------- import


# -------------------------------------------------------------- single CRUD


class ThreatUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    references: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] | None = None


class ControlUpsert(BaseModel):
    framework: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=120)


class BenchmarkUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str | None = Field(default=None, max_length=120)
    metric: str = Field(min_length=1, max_length=80)
    distribution: dict[str, Any]
    citation: str | None = Field(default=None, max_length=400)


def _ensure_editable(source: str) -> None:
    """No-op gate (kept for symmetry across the three resource types).

    All catalogue entries — including the ones bundled by the seeder — are
    editable. The bootstrap seeder is idempotent on `public_id`, so:

        * user edits to a built-in row PERSIST across restarts (seeder skips
          existing rows of the same public_id).
        * deleting a built-in row REMOVES it for that DB; on the next startup
          the original is re-seeded, which gives users a no-fuss reset path.
    """
    return None


@router.post("/threats", response_model=ThreatRead, status_code=status.HTTP_201_CREATED)
def create_threat(
    payload: ThreatUpsert, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = ThreatEntry(public_id=_short_id("user-threat"), source="user", **payload.model_dump())
    db.add(row)
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.CREATE,
        entity_type="knowledge.threat",
        entity_id=row.public_id,
        summary=f"Created threat '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return _t(row)


@router.patch("/threats/{public_id}", response_model=ThreatRead)
def update_threat(
    public_id: str,
    payload: ThreatUpsert,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    row = db.exec(select(ThreatEntry).where(ThreatEntry.public_id == public_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Threat not found")
    _ensure_editable(row.source)
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    row.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.UPDATE,
        entity_type="knowledge.threat",
        entity_id=row.public_id,
        summary=f"Updated threat '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return _t(row)


@router.delete("/threats/{public_id}", response_model=Message)
def delete_threat(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = db.exec(select(ThreatEntry).where(ThreatEntry.public_id == public_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Threat not found")
    _ensure_editable(row.source)
    db.delete(row)
    audit.record(
        db,
        actor=user,
        action=AuditAction.DELETE,
        entity_type="knowledge.threat",
        entity_id=public_id,
        summary=f"Deleted threat '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return Message(message="Deleted")


@router.post("/controls", response_model=ControlRead, status_code=status.HTTP_201_CREATED)
def create_control(
    payload: ControlUpsert, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = ControlEntry(public_id=_short_id("user-control"), source="user", **payload.model_dump())
    db.add(row)
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.CREATE,
        entity_type="knowledge.control",
        entity_id=row.public_id,
        summary=f"Created control {row.code} '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return _c(row)


@router.patch("/controls/{public_id}", response_model=ControlRead)
def update_control(
    public_id: str,
    payload: ControlUpsert,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    row = db.exec(select(ControlEntry).where(ControlEntry.public_id == public_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Control not found")
    _ensure_editable(row.source)
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    row.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.UPDATE,
        entity_type="knowledge.control",
        entity_id=row.public_id,
        summary=f"Updated control {row.code}",
        request_id=request_id,
    )
    db.commit()
    return _c(row)


@router.delete("/controls/{public_id}", response_model=Message)
def delete_control(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = db.exec(select(ControlEntry).where(ControlEntry.public_id == public_id)).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Control not found")
    _ensure_editable(row.source)
    db.delete(row)
    audit.record(
        db,
        actor=user,
        action=AuditAction.DELETE,
        entity_type="knowledge.control",
        entity_id=public_id,
        summary=f"Deleted control {row.code}",
        request_id=request_id,
    )
    db.commit()
    return Message(message="Deleted")


@router.post("/benchmarks", response_model=BenchmarkRead, status_code=status.HTTP_201_CREATED)
def create_benchmark(
    payload: BenchmarkUpsert, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = BenchmarkEntry(
        public_id=_short_id("user-bench"), source="user", **payload.model_dump()
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.CREATE,
        entity_type="knowledge.benchmark",
        entity_id=row.public_id,
        summary=f"Created benchmark '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return _b(row)


@router.patch("/benchmarks/{public_id}", response_model=BenchmarkRead)
def update_benchmark(
    public_id: str,
    payload: BenchmarkUpsert,
    db: SessionDep,
    user: ReviewerUser,
    request_id: RequestId,
):
    row = db.exec(
        select(BenchmarkEntry).where(BenchmarkEntry.public_id == public_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Benchmark not found")
    _ensure_editable(row.source)
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    row.updated_at = utcnow()
    db.flush()
    audit.record(
        db,
        actor=user,
        action=AuditAction.UPDATE,
        entity_type="knowledge.benchmark",
        entity_id=row.public_id,
        summary=f"Updated benchmark '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return _b(row)


@router.delete("/benchmarks/{public_id}", response_model=Message)
def delete_benchmark(
    public_id: str, db: SessionDep, user: ReviewerUser, request_id: RequestId
):
    row = db.exec(
        select(BenchmarkEntry).where(BenchmarkEntry.public_id == public_id)
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Benchmark not found")
    _ensure_editable(row.source)
    db.delete(row)
    audit.record(
        db,
        actor=user,
        action=AuditAction.DELETE,
        entity_type="knowledge.benchmark",
        entity_id=public_id,
        summary=f"Deleted benchmark '{row.name}'",
        request_id=request_id,
    )
    db.commit()
    return Message(message="Deleted")


# -------------------------------------------------------------- bulk import


@router.post(
    "/import",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def import_catalogue(
    kind: str,
    source: str,
    file: UploadFile,
    db: SessionDep,
    owner: OwnerUser,
    request_id: RequestId,
):
    """Upload a JSON catalogue. The JSON must be a list of objects matching
    the target shape — see /docs for each model's fields."""
    import json

    if kind not in {"threats", "controls", "benchmarks"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind must be threats|controls|benchmarks")
    body = await file.read()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Expected a JSON array")

    inserted = 0
    for item in payload:
        if not isinstance(item, dict) or "public_id" not in item:
            continue
        existing = None
        if kind == "threats":
            existing = db.exec(
                select(ThreatEntry).where(ThreatEntry.public_id == item["public_id"])
            ).first()
            if existing:
                continue
            db.add(ThreatEntry(source=source, **item))
        elif kind == "controls":
            existing = db.exec(
                select(ControlEntry).where(ControlEntry.public_id == item["public_id"])
            ).first()
            if existing:
                continue
            db.add(ControlEntry(source=source, **item))
        else:
            existing = db.exec(
                select(BenchmarkEntry).where(BenchmarkEntry.public_id == item["public_id"])
            ).first()
            if existing:
                continue
            db.add(BenchmarkEntry(source=source, **item))
        inserted += 1
    audit.record(
        db,
        actor=owner,
        action=AuditAction.IMPORT,
        entity_type=f"knowledge.{kind}",
        entity_id=source,
        summary=f"Imported {inserted} {kind} entries from source '{source}'",
        request_id=request_id,
    )
    db.commit()
    return Message(message=f"Imported {inserted} {kind} entries from '{source}'")
