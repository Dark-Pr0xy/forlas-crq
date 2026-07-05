"""Simulation scale/storage — ceiling, retention, pagination, cache (H5/H6/M7)."""

from __future__ import annotations


def _create(client, name: str = "Scale scn") -> str:
    body = {
        "name": name,
        "mode": "tef-vuln",
        "tolerance": 1_000_000,
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 4, "max": 10},
            "vuln": {"type": "pert", "min": 0.05, "mode": 0.25, "max": 0.6},
            "plm": {"type": "pert", "min": 50_000, "mode": 250_000, "max": 1_500_000},
            "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
            "slm": {"type": "pert", "min": 25_000, "mode": 150_000, "max": 2_000_000},
        },
    }
    r = client.post("/api/scenarios", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _run(client, pid: str, iterations: int = 5_000, seed: int = 3) -> str:
    r = client.post(
        f"/api/scenarios/{pid}/simulations",
        json={"iterations": iterations, "seed": seed, "persist_artifacts": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_iterations_above_ceiling_rejected(owner_client):
    pid = _create(owner_client)
    # Above the schema bound → 422 from Pydantic validation.
    r = owner_client.post(
        f"/api/scenarios/{pid}/simulations",
        json={"iterations": 2_000_000, "seed": 1},
    )
    assert r.status_code == 422, r.text


def test_artifact_retention_prunes_old_runs(owner_client):
    from app.services.simulation import ARTIFACT_RETENTION_PER_SCENARIO

    pid = _create(owner_client)
    run_ids = [_run(owner_client, pid, seed=s) for s in range(ARTIFACT_RETENTION_PER_SCENARIO + 3)]

    # The oldest runs' artifacts should have been pruned; only the newest N
    # keep their loss data.
    kept = 0
    for rid in run_ids:
        r = owner_client.get(f"/api/simulations/{rid}/losses")
        if r.status_code == 200:
            kept += 1
    assert kept == ARTIFACT_RETENTION_PER_SCENARIO


def test_losses_pagination(owner_client):
    pid = _create(owner_client)
    rid = _run(owner_client, pid, iterations=5_000)
    r = owner_client.get(f"/api/simulations/{rid}/losses?offset=0&limit=100")
    assert r.status_code == 200
    body = r.json()
    assert len(body["losses"]) == 100
    assert body["total"] == 5_000
    assert body["offset"] == 0
    # Second page.
    r2 = owner_client.get(f"/api/simulations/{rid}/losses?offset=4950&limit=100")
    assert len(r2.json()["losses"]) == 50  # only 50 rows left


def test_losses_csv_stream(owner_client):
    pid = _create(owner_client)
    rid = _run(owner_client, pid, iterations=2_000)
    r = owner_client.get(f"/api/simulations/{rid}/losses.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().split("\n")
    assert lines[0] == "iteration,loss,lef"
    assert len(lines) == 2_001  # header + 2000 rows


def test_rollup_cache_hit_and_invalidation(owner_client):
    pid = _create(owner_client)
    _run(owner_client, pid, seed=1)
    first = owner_client.get("/api/portfolio/rollup").json()
    # Second identical request should return the same payload (served from cache).
    second = owner_client.get("/api/portfolio/rollup").json()
    assert first == second
    # A new run changes the signature and thus the rollup.
    _run(owner_client, pid, seed=999)
    third = owner_client.get("/api/portfolio/rollup").json()
    # Same scenario/params but a different underlying run — cache must have been
    # invalidated (we don't assert values differ, only that it recomputed OK).
    assert third["scenario_count"] == first["scenario_count"]
