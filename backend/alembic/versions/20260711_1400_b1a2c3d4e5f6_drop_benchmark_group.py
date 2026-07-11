"""drop scenarios.benchmark_group

The free-text ``benchmark_group`` field was populated by the demo seeder and
round-tripped through the API, but nothing consumed it (no aggregation, no
filtering). Retired to reduce metadata noise.

Revision ID: b1a2c3d4e5f6
Revises: 6f17c7062a65
Create Date: 2026-07-11 14:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "b1a2c3d4e5f6"
down_revision: str | None = "6f17c7062a65"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.drop_column("benchmark_group")


def downgrade() -> None:
    with op.batch_alter_table("scenarios", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "benchmark_group",
                sqlmodel.sql.sqltypes.AutoString(length=120),
                nullable=True,
            )
        )
