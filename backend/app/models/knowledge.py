"""Knowledge library: threat communities, controls, benchmarks, reference assumptions."""

from __future__ import annotations

from typing import Any

from sqlmodel import Field, SQLModel

from app.models._base import TimestampMixin, json_column, nullable_json_column


class ThreatEntry(TimestampMixin, SQLModel, table=True):
    __tablename__ = "knowledge_threats"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=64)
    name: str = Field(index=True, max_length=200)
    category: str | None = Field(default=None, max_length=120, index=True)
    source: str = Field(default="builtin", max_length=64, index=True)
    description: str | None = Field(default=None, max_length=4000)
    references: list[str] = Field(default_factory=list, sa_column=json_column())
    attributes: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())


class ControlEntry(TimestampMixin, SQLModel, table=True):
    __tablename__ = "knowledge_controls"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=64)
    framework: str = Field(index=True, max_length=64)  # e.g. NIST CSF 2.0, CIS v8.1, ISO 27001
    code: str = Field(index=True, max_length=64)
    name: str = Field(max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    category: str | None = Field(default=None, max_length=120)
    source: str = Field(default="builtin", max_length=64, index=True)
    attributes: dict[str, Any] | None = Field(default=None, sa_column=nullable_json_column())


class BenchmarkEntry(TimestampMixin, SQLModel, table=True):
    """Reference assumption (e.g. industry frequency/magnitude ranges)."""

    __tablename__ = "knowledge_benchmarks"

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(index=True, unique=True, max_length=64)
    name: str = Field(max_length=200, index=True)
    industry: str | None = Field(default=None, max_length=120, index=True)
    metric: str = Field(max_length=80, index=True)  # e.g. tef, plm, slp_prob
    distribution: dict[str, Any] = Field(sa_column=json_column())
    citation: str | None = Field(default=None, max_length=400)
    source: str = Field(default="builtin", max_length=64, index=True)
