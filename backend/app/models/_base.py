"""Shared mixins and column helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin(SQLModel):
    """Adds created_at / updated_at columns. Application updates updated_at."""

    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)


def json_column() -> Column:
    """SQLite JSON column factory (uses TEXT under the hood)."""
    return Column(JSON, nullable=False)


def nullable_json_column() -> Column:
    return Column(JSON, nullable=True)


class Role(str, Enum):
    OWNER = "owner"
    APPROVER = "approver"
    REVIEWER = "reviewer"
    READONLY = "readonly"

    @classmethod
    def rank(cls, value: "Role | str") -> int:
        order = [cls.READONLY, cls.REVIEWER, cls.APPROVER, cls.OWNER]
        return order.index(cls(value))


class ApprovalState(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class DecompositionMode(str, Enum):
    LEF = "lef"
    TEF_VULN = "tef-vuln"
    FULL = "full"


class DistributionType(str, Enum):
    PERT = "pert"
    TRIANGULAR = "triangular"
    UNIFORM = "uniform"
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    BETA = "beta"
    GAMMA = "gamma"


class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    SIMULATE = "simulate"
    SNAPSHOT = "snapshot"
    APPROVE = "approve"
    SUBMIT_FOR_REVIEW = "submit_for_review"
    REJECT = "reject"
    ARCHIVE = "archive"
    EXPORT = "export"
    IMPORT = "import"
