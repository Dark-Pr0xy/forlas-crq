"""add analysis_records

One analysis & evidence record per scenario: narrative, confidence, and the
structured lists of data sources, assumptions and gaps, plus optional
per-FAIR-input rationale.

Revision ID: c2b3d4e5f6a7
Revises: b1a2c3d4e5f6
Create Date: 2026-07-11 14:10:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "c2b3d4e5f6a7"
down_revision: str | None = "b1a2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_records",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.Integer(), nullable=False),
        sa.Column("summary", sqlmodel.sql.sqltypes.AutoString(length=16000), nullable=True),
        sa.Column("confidence", sqlmodel.sql.sqltypes.AutoString(length=24), nullable=True),
        sa.Column("data_sources", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("input_rationale", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenarios.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("analysis_records", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_analysis_records_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_analysis_records_updated_at"), ["updated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_analysis_records_scenario_id"), ["scenario_id"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_analysis_records_scenario_id"))
        batch_op.drop_index(batch_op.f("ix_analysis_records_updated_at"))
        batch_op.drop_index(batch_op.f("ix_analysis_records_created_at"))
    op.drop_table("analysis_records")
