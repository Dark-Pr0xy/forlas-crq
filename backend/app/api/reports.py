"""Reporting endpoints — HTML for print-to-PDF and DOCX for download."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from sqlmodel import select

from app.deps import CurrentUser, RequestId, SessionDep
from app.models._base import AuditAction
from app.models.scenario import Scenario
from app.reporting import build_docx_report, build_report_context, render_html_report
from app.services import audit
from app.services import scenario as scn_svc

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportRequest(BaseModel):
    kind: Literal["executive", "board"] = "executive"
    scope: Literal["portfolio", "individual", "both"] = "both"
    scenario_ids: list[str] | None = None
    appetite: float | None = None
    title: str | None = None


def _resolve_scenarios(db: SessionDep, ids: list[str] | None) -> list[Scenario]:
    # Distinguish:
    #   - ids is None       → caller didn't specify, default to all scenarios
    #   - ids is empty list  → caller explicitly deselected everything; refuse
    #   - ids is non-empty   → render exactly those
    if ids is None:
        return scn_svc.list_scenarios(db)
    if len(ids) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Select at least one scenario before generating a report.",
        )
    rows = db.exec(select(Scenario).where(Scenario.public_id.in_(ids))).all()
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No scenarios matched")
    return list(rows)


@router.post("/html", response_class=HTMLResponse)
def render_html(
    payload: ReportRequest,
    db: SessionDep,
    user: CurrentUser,
    request_id: RequestId,
):
    scenarios = _resolve_scenarios(db, payload.scenario_ids)
    context = build_report_context(
        db,
        scenarios=scenarios,
        appetite=payload.appetite,
        title=payload.title,
        kind=payload.kind,
    )
    html = render_html_report(context)
    audit.record(
        db,
        actor=user,
        action=AuditAction.EXPORT,
        entity_type="report",
        entity_id=payload.kind,
        summary=f"Rendered {payload.kind} HTML report over {len(scenarios)} scenario(s)",
        request_id=request_id,
    )
    db.commit()
    return HTMLResponse(content=html)


@router.post("/docx")
def render_docx(
    payload: ReportRequest,
    db: SessionDep,
    user: CurrentUser,
    request_id: RequestId,
):
    scenarios = _resolve_scenarios(db, payload.scenario_ids)
    context = build_report_context(
        db,
        scenarios=scenarios,
        appetite=payload.appetite,
        title=payload.title,
        kind=payload.kind,
    )
    blob = build_docx_report(context)
    audit.record(
        db,
        actor=user,
        action=AuditAction.EXPORT,
        entity_type="report",
        entity_id=payload.kind,
        summary=f"Generated {payload.kind} DOCX over {len(scenarios)} scenario(s)",
        request_id=request_id,
    )
    db.commit()
    filename = f"forlas_{payload.kind}_report.docx"
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
