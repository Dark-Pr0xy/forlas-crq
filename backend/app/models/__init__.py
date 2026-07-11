"""SQLModel ORM classes.

`register_all` imports every submodule so SQLModel.metadata is populated for
Alembic autogeneration and `SQLModel.metadata.create_all` (used in tests).
"""

from __future__ import annotations


def register_all() -> None:
    from app.models import (  # noqa: F401
        analysis,
        approval,
        audit,
        knowledge,
        portfolio,
        scenario,
        session,
        settings,
        simulation,
        user,
    )


register_all()
