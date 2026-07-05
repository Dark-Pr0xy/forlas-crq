"""RBAC + governance enforcement (CODE_REVIEW H1, H2, H3)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import make_app


def _scenario_body(name: str = "RBAC scn") -> dict:
    return {
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


def _make_user(owner_client, email: str, role: str, password: str = "TestPass1!") -> int:
    r = owner_client.post(
        "/api/auth/users",
        json={"email": email, "display_name": email, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _client_for(email: str, password: str = "TestPass1!") -> TestClient:
    c = TestClient(make_app())
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return c


# ---------------------------------------------------------------- H1 draft lock


def test_cannot_edit_model_of_approved_scenario(owner_client):
    r = owner_client.post("/api/scenarios", json=_scenario_body())
    pid = r.json()["id"]
    # draft → in_review → approved
    owner_client.post(f"/api/governance/scenarios/{pid}/transition", json={"action": "submit_for_review"})
    owner_client.post(f"/api/governance/scenarios/{pid}/transition", json={"action": "approve"})

    # Changing the model is now blocked with 409.
    r = owner_client.patch(f"/api/scenarios/{pid}", json={"tolerance": 2_000_000})
    assert r.status_code == 409, r.text
    assert "draft" in r.json()["detail"].lower()


def test_can_edit_metadata_of_approved_scenario(owner_client):
    r = owner_client.post("/api/scenarios", json=_scenario_body())
    pid = r.json()["id"]
    owner_client.post(f"/api/governance/scenarios/{pid}/transition", json={"action": "submit_for_review"})
    owner_client.post(f"/api/governance/scenarios/{pid}/transition", json={"action": "approve"})

    # Non-modelling metadata (notes) is still editable.
    r = owner_client.patch(f"/api/scenarios/{pid}", json={"notes": "post-approval annotation"})
    assert r.status_code == 200, r.text
    assert r.json()["notes"] == "post-approval annotation"


def test_draft_scenario_model_is_editable(owner_client):
    r = owner_client.post("/api/scenarios", json=_scenario_body())
    pid = r.json()["id"]
    r = owner_client.patch(f"/api/scenarios/{pid}", json={"tolerance": 3_000_000})
    assert r.status_code == 200
    assert r.json()["tolerance"] == 3_000_000


# ---------------------------------------------------------------- H2 ownership


def test_reviewer_cannot_edit_others_scenario(owner_client):
    # Owner creates a scenario (owned by owner).
    pid = owner_client.post("/api/scenarios", json=_scenario_body("owned by owner")).json()["id"]

    _make_user(owner_client, "rev@local", "reviewer")
    reviewer = _client_for("rev@local")
    r = reviewer.patch(f"/api/scenarios/{pid}", json={"notes": "sneaky"})
    assert r.status_code == 403, r.text


def test_reviewer_can_edit_own_scenario(owner_client):
    _make_user(owner_client, "rev2@local", "reviewer")
    reviewer = _client_for("rev2@local")
    pid = reviewer.post("/api/scenarios", json=_scenario_body("owned by reviewer")).json()["id"]
    r = reviewer.patch(f"/api/scenarios/{pid}", json={"notes": "mine to edit"})
    assert r.status_code == 200, r.text


def test_approver_can_edit_any_scenario(owner_client):
    pid = owner_client.post("/api/scenarios", json=_scenario_body("owner's")).json()["id"]
    _make_user(owner_client, "app@local", "approver")
    approver = _client_for("app@local")
    r = approver.patch(f"/api/scenarios/{pid}", json={"notes": "approver override"})
    assert r.status_code == 200, r.text


def test_ownership_transfer(owner_client):
    pid = owner_client.post("/api/scenarios", json=_scenario_body()).json()["id"]
    new_owner_id = _make_user(owner_client, "newowner@local", "reviewer")
    r = owner_client.post(
        f"/api/scenarios/{pid}/transfer-ownership",
        json={"new_owner_user_id": new_owner_id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["owner_user_id"] == new_owner_id
    # The new owner can now edit it.
    newc = _client_for("newowner@local")
    assert newc.patch(f"/api/scenarios/{pid}", json={"notes": "now mine"}).status_code == 200


# ---------------------------------------------------------------- H3 schedules/settings


def test_readonly_cannot_upsert_schedule(owner_client):
    pid = owner_client.post("/api/scenarios", json=_scenario_body()).json()["id"]
    _make_user(owner_client, "ro@local", "readonly")
    ro = _client_for("ro@local")
    r = ro.put(f"/api/governance/scenarios/{pid}/schedule", json={"cadence_days": 90})
    assert r.status_code == 403, r.text


def test_reviewer_can_upsert_schedule(owner_client):
    pid = owner_client.post("/api/scenarios", json=_scenario_body()).json()["id"]
    _make_user(owner_client, "rev3@local", "reviewer")
    rev = _client_for("rev3@local")
    r = rev.put(f"/api/governance/scenarios/{pid}/schedule", json={"cadence_days": 90})
    assert r.status_code == 200, r.text


def test_reviewer_cannot_change_settings(owner_client):
    _make_user(owner_client, "rev4@local", "reviewer")
    rev = _client_for("rev4@local")
    r = rev.patch("/api/settings", json={"iterations": 50_000})
    assert r.status_code == 403, r.text


def test_owner_can_change_settings(owner_client):
    r = owner_client.patch("/api/settings", json={"iterations": 50_000})
    assert r.status_code == 200, r.text
    assert r.json()["iterations"] == 50_000


# ---------------------------------------------------------------- M8 restore


def test_soft_delete_then_restore(owner_client):
    pid = owner_client.post("/api/scenarios", json=_scenario_body()).json()["id"]
    assert owner_client.delete(f"/api/scenarios/{pid}").status_code == 200
    # Gone from the main list.
    assert all(s["id"] != pid for s in owner_client.get("/api/scenarios").json())
    # Present in the deleted list.
    assert any(s["id"] == pid for s in owner_client.get("/api/scenarios/deleted").json())
    # Restore brings it back.
    assert owner_client.post(f"/api/scenarios/{pid}/restore").status_code == 200
    assert any(s["id"] == pid for s in owner_client.get("/api/scenarios").json())
