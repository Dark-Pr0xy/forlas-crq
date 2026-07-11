"""Analysis & evidence DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DataSource(BaseModel):
    """A piece of data or evidence relied on during the analysis."""

    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    reference: str | None = Field(default=None, max_length=1000)  # URL, doc ref or citation
    date: str | None = Field(default=None, max_length=24)
    confidence: str | None = Field(default=None, max_length=24)  # low | medium | high


class Assumption(BaseModel):
    statement: str = Field(min_length=1, max_length=2000)
    rationale: str | None = Field(default=None, max_length=4000)
    impact: str | None = Field(default=None, max_length=2000)  # impact if the assumption is wrong


class Gap(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    severity: str | None = Field(default=None, max_length=24)  # low | medium | high
    mitigation: str | None = Field(default=None, max_length=2000)


class AnalysisRead(BaseModel):
    scenario_id: str
    summary: str | None
    confidence: str | None
    data_sources: list[DataSource]
    assumptions: list[Assumption]
    gaps: list[Gap]
    input_rationale: dict[str, str]
    updated_at: datetime | None
    updated_by_user_id: int | None


class AnalysisUpdate(BaseModel):
    summary: str | None = Field(default=None, max_length=16000)
    confidence: str | None = Field(default=None, max_length=24)
    data_sources: list[DataSource] | None = None
    assumptions: list[Assumption] | None = None
    gaps: list[Gap] | None = None
    input_rationale: dict[str, str] | None = None
