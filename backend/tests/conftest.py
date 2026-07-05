"""Shared pytest fixtures.

Every test gets an isolated, in-memory SQLite + TestClient so they're parallel-
safe and don't touch the user's real data directory.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(monkeypatch) -> Iterator[Path]:
    """Per-test data dir + fresh engine.

    `app.config.settings` is a module-level singleton, so we mutate its fields
    in place (rather than rebinding) to keep references in already-imported
    modules pointing at the same object. The DB engine cache is cleared so the
    lifespan rebuilds it against the new SQLite file.
    """
    with tempfile.TemporaryDirectory(prefix="forlas-test-") as tmp:
        monkeypatch.setenv("FORLAS_DATA_DIR", tmp)
        monkeypatch.setenv("FORLAS_SEED_DEMO_SCENARIOS", "false")
        monkeypatch.setenv("FORLAS_BOOTSTRAP_OWNER_PASSWORD", "Test1234!")

        import app.config
        import app.db
        from app.config import Settings

        fresh = Settings()
        fresh.ensure_dirs()
        for field in fresh.__class__.model_fields:
            object.__setattr__(app.config.settings, field, getattr(fresh, field))
        app.db._engine = None

        yield Path(tmp)


@pytest.fixture
def client(isolated_data_dir):
    # Import lazily so settings pick up env-var overrides
    from fastapi.testclient import TestClient

    from app.main import make_app

    app = make_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def owner_client(client):
    from app.config import settings

    r = client.post(
        "/api/auth/login",
        json={
            "email": settings.bootstrap_owner_email,
            "password": "Test1234!",
        },
    )
    assert r.status_code == 200, r.text
    return client
