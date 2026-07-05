"""Smoke tests covering the Phase 1 surface area."""

from __future__ import annotations

import pytest


def test_health_open(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["name"] == "FORLAS CRQ"


def test_session_unauthenticated(client):
    r = client.get("/api/auth/session")
    assert r.status_code == 200
    assert r.json()["authenticated"] is False


def test_scenarios_require_auth(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 401


def test_owner_login_and_create_scenario(owner_client):
    sess = owner_client.get("/api/auth/session").json()
    assert sess["authenticated"]
    assert sess["user"]["role"] == "owner"

    body = {
        "name": "Test scenario",
        "tags": ["smoke"],
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
    r = owner_client.post("/api/scenarios", json=body)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["name"] == "Test scenario"
    public_id = created["id"]

    # round-trip
    r = owner_client.get(f"/api/scenarios/{public_id}")
    assert r.status_code == 200
    assert r.json()["tolerance"] == 1_000_000

    # update
    r = owner_client.patch(
        f"/api/scenarios/{public_id}",
        json={"description": "added later", "snapshot_note": "first save"},
    )
    assert r.status_code == 200
    assert r.json()["description"] == "added later"

    # clone
    r = owner_client.post(f"/api/scenarios/{public_id}/clone")
    assert r.status_code == 200
    assert r.json()["name"].endswith("(copy)")

    # list
    r = owner_client.get("/api/scenarios")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_ula_acknowledgement(owner_client):
    r = owner_client.post("/api/ula/acknowledge", json={"version": "1.0"})
    assert r.status_code == 200
    sess = owner_client.get("/api/auth/session").json()
    assert sess["ula_acknowledged"]
    assert sess["ula_version"] == "1.0"


def test_alpha_importer(owner_client):
    import io
    import json

    payload = json.dumps(
        {
            "scenarios": [
                {
                    "name": "Imported",
                    "bu": "Ops",
                    "mode": "tef-vuln",
                    "tolerance": 500000,
                    "inputs": {
                        "tef": {"type": "pert", "min": 1, "mode": 4, "max": 10},
                        "vuln": {"type": "pert", "min": 0.05, "mode": 0.25, "max": 0.6},
                        "plm": {"type": "pert", "min": 50000, "mode": 250000, "max": 1500000},
                        "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
                        "slm": {"type": "pert", "min": 25000, "mode": 150000, "max": 2000000},
                    },
                }
            ]
        }
    ).encode()
    r = owner_client.post(
        "/api/import/alpha",
        files={"file": ("alpha.json", io.BytesIO(payload), "application/json")},
    )
    assert r.status_code == 201, r.text
    assert "Imported 1" in r.json()["message"]


def test_invalid_distribution_rejected(owner_client):
    body = {
        "name": "Bad",
        "mode": "tef-vuln",
        "inputs": {
            "tef": {"type": "pert", "min": 5, "mode": 1, "max": 10},  # mode < min
            "vuln": {"type": "pert", "min": 0, "mode": 0.5, "max": 1},
            "plm": {"type": "pert", "min": 1, "mode": 2, "max": 3},
            "slp_prob": {"type": "pert", "min": 0, "mode": 0.5, "max": 1},
            "slm": {"type": "pert", "min": 1, "mode": 2, "max": 3},
        },
    }
    r = owner_client.post("/api/scenarios", json=body)
    assert r.status_code == 422
