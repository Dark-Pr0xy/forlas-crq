"""Analysis & evidence captured against a scenario.

One record per scenario. Holds the qualitative reasoning behind the numbers:
the analyst's narrative, the data they relied on, the assumptions they made,
the gaps/limitations they are aware of, and (optionally) a short rationale for
each FAIR input. This is the audit trail a reviewer reads to judge whether the
quantified estimate is defensible.
"""

from __future__ import annotations

from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import TimestampMixin, json_column


class AnalysisRecord(TimestampMixin, SQLModel, table=True):
    __tablename__ = "analysis_records"

    id: int | None = Field(default=None, primary_key=True)
    scenario_id: int = Field(foreign_key="scenarios.id", index=True, unique=True)

    # Free-text narrative of the analysis and overall confidence in it.
    summary: str | None = Field(default=None, max_length=16000)
    confidence: str | None = Field(default=None, max_length=24)  # low | medium | high

    # Structured lists of dicts (shapes validated by the API schema):
    #   data_sources: {title, description, reference, date, confidence}
    #   assumptions:  {statement, rationale, impact}
    #   gaps:         {description, severity, mitigation}
    data_sources: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())
    assumptions: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())
    gaps: list[dict[str, Any]] = Field(default_factory=list, sa_column=json_column())

    # Optional per-FAIR-variable rationale, keyed by input name (lef, tef, ...).
    input_rationale: dict[str, str] = Field(default_factory=dict, sa_column=json_column())

    updated_by_user_id: int | None = Field(default=None, foreign_key="users.id")
