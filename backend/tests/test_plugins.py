"""Plugin host tests.

We don't install a package via entry points in tests; instead we register a
manifest directly into the global registry, which is the same code path that
runs after entry-point discovery.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.engine.distributions import sample
from app.engine.rng import default_rng


@pytest.fixture(autouse=True)
def reset_registry():
    """Each test starts with a clean registry."""
    from app.plugins import registry

    registry.manifests.clear()
    registry.distributions.clear()
    registry.exporters.clear()
    registry.knowledge.clear()
    registry.discovered = False
    yield
    registry.manifests.clear()
    registry.distributions.clear()
    registry.exporters.clear()
    registry.knowledge.clear()
    registry.discovered = False


def test_registers_distribution_and_engine_uses_it():
    from app.plugins import registry
    from tests.fixtures.demo_plugin import plugin

    registry.register(plugin)
    rng = default_rng(42)
    samples = sample(rng, 10_000, {"type": "weibull", "shape": 1.5, "max": 100})
    assert samples.min() >= 0
    assert samples.mean() > 0
    # Distribution is now in the registry surface
    assert "weibull" in registry.distributions


def test_plugin_knowledge_seeded(owner_client):
    """Plugin knowledge surfaces in the knowledge API after a re-bootstrap.

    The conftest tears down and recreates the app per test, so registering the
    plugin in this test process is enough — the next /api/knowledge/threats
    query will reflect it via the seed path.
    """
    from sqlmodel import Session, select

    from app.db import get_engine
    from app.knowledge.seed import seed_knowledge
    from app.models.knowledge import ThreatEntry
    from app.plugins import registry
    from tests.fixtures.demo_plugin import plugin

    registry.register(plugin)

    with Session(get_engine()) as db:
        counts = seed_knowledge(db)
        db.commit()
        assert counts["threats"] >= 1
        row = db.exec(
            select(ThreatEntry).where(ThreatEntry.public_id == "demo-plugin-threat")
        ).first()
        assert row is not None
        assert row.source == "demo-plugin"
        assert row.name == "Plugin-contributed threat"


def test_plugin_list_endpoint(owner_client):
    from app.plugins import registry
    from tests.fixtures.demo_plugin import plugin

    registry.register(plugin)
    r = owner_client.get("/api/plugins")
    assert r.status_code == 200, r.text
    plugins = r.json()
    assert any(p["name"] == "forlas-demo-plugin" for p in plugins)
    found = next(p for p in plugins if p["name"] == "forlas-demo-plugin")
    assert "weibull" in found["distributions"]
    assert "xlsx-summary" in found["exporters"]


def test_duplicate_registration_skipped(caplog):
    from app.plugins import registry
    from tests.fixtures.demo_plugin import plugin

    registry.register(plugin)
    registry.register(plugin)  # second time is a no-op
    assert len([m for m in registry.manifests if m.name == plugin.name]) == 1
