"""End-to-end test for the simulation API surface."""

from __future__ import annotations


def _make_scenario(client) -> str:
    body = {
        "name": "API sim test",
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


def test_simulation_round_trip(owner_client):
    public_id = _make_scenario(owner_client)
    r = owner_client.post(
        f"/api/scenarios/{public_id}/simulations",
        json={"iterations": 10_000, "seed": 42, "persist_artifacts": True},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["statistics"]["iterations"] == 10_000
    assert body["statistics"]["mean"] > 0
    assert body["histogram"] is not None
    assert body["lec_curve"] is not None
    assert body["losses_url"]
    run_id = body["id"]

    # Paginated endpoint: default page caps at 5000; total reports the full run.
    r2 = owner_client.get(f"/api/simulations/{run_id}/losses")
    assert r2.status_code == 200
    assert r2.json()["total"] == 10_000
    assert len(r2.json()["losses"]) == 5_000
    # Explicit larger page returns the whole vector.
    r3 = owner_client.get(f"/api/simulations/{run_id}/losses?limit=10000")
    assert len(r3.json()["losses"]) == 10_000

    latest = owner_client.get(f"/api/scenarios/{public_id}/simulations/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == run_id


def test_no_simulation_yet(owner_client):
    public_id = _make_scenario(owner_client)
    r = owner_client.get(f"/api/scenarios/{public_id}/simulations/latest")
    assert r.status_code == 404


def test_readonly_user_cannot_trigger(owner_client):
    public_id = _make_scenario(owner_client)
    # Create a readonly user via the user-management endpoint
    r = owner_client.post(
        "/api/auth/users",
        json={
            "email": "ro@local",
            "display_name": "Read-only",
            "password": "Readonly1!",
            "role": "readonly",
        },
    )
    assert r.status_code == 201, r.text
    # Sign in as the readonly user
    owner_client.post("/api/auth/logout")
    r = owner_client.post(
        "/api/auth/login",
        json={"email": "ro@local", "password": "Readonly1!"},
    )
    assert r.status_code == 200
    r = owner_client.post(
        f"/api/scenarios/{public_id}/simulations",
        json={"iterations": 5000, "seed": 1},
    )
    assert r.status_code == 403
