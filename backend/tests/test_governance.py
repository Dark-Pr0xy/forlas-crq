"""Governance tests — approval state machine, RBAC, schedules, audit visibility."""

from __future__ import annotations


def _create_scenario(client) -> str:
    body = {
        "name": "Approval scn",
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


def _create_user(client, email: str, role: str, password: str = "TestPass1!") -> int:
    r = client.post(
        "/api/auth/users",
        json={"email": email, "display_name": email, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _login_as(client, email: str, password: str = "TestPass1!") -> None:
    client.post("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


# -------------------------------------------------------------- state machine


def test_approval_happy_path(owner_client):
    public_id = _create_scenario(owner_client)
    # draft → in_review (owner is also a reviewer)
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "submit_for_review", "note": "ready"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["state"] == "in_review"
    # in_review → approved
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "approve", "note": "looks good"},
    )
    assert r.status_code == 201
    assert r.json()["state"] == "approved"
    # approved → archived
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "archive"},
    )
    assert r.status_code == 201
    assert r.json()["state"] == "archived"
    # archived → draft (reopen)
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "reopen"},
    )
    assert r.status_code == 201
    assert r.json()["state"] == "draft"

    r = owner_client.get(f"/api/scenarios/{public_id}")
    assert r.json()["approval_state"] == "draft"


def test_invalid_transition_rejected(owner_client):
    public_id = _create_scenario(owner_client)
    # Cannot approve from draft
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "approve"},
    )
    assert r.status_code == 409
    # Cannot archive from draft
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "archive"},
    )
    assert r.status_code == 409


def test_reviewer_cannot_approve(owner_client):
    _create_user(owner_client, "reviewer@local", "reviewer")
    public_id = _create_scenario(owner_client)
    # owner submits for review
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "submit_for_review"},
    )
    assert r.status_code == 201
    # sign in as reviewer
    _login_as(owner_client, "reviewer@local")
    # reviewer cannot approve
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "approve"},
    )
    assert r.status_code == 403


def test_readonly_cannot_transition(owner_client):
    _create_user(owner_client, "ro@local", "readonly")
    public_id = _create_scenario(owner_client)
    _login_as(owner_client, "ro@local")
    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/transition",
        json={"action": "submit_for_review"},
    )
    assert r.status_code == 403


# -------------------------------------------------------------- schedules


def test_review_schedule_lifecycle(owner_client):
    public_id = _create_scenario(owner_client)
    r = owner_client.put(
        f"/api/governance/scenarios/{public_id}/schedule",
        json={"cadence_days": 90},
    )
    assert r.status_code == 200, r.text
    sched = r.json()
    assert sched["cadence_days"] == 90
    assert sched["active"] is True

    r = owner_client.post(
        f"/api/governance/scenarios/{public_id}/schedule/mark-reviewed",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["last_reviewed_at"] is not None

    r = owner_client.get("/api/governance/schedules")
    assert r.status_code == 200
    assert any(s["entity_id"] == sched["entity_id"] for s in r.json())


# -------------------------------------------------------------- change history


def test_change_history_uses_snapshot_notes(owner_client):
    public_id = _create_scenario(owner_client)
    r = owner_client.patch(
        f"/api/scenarios/{public_id}",
        json={"description": "first save", "snapshot_note": "initial baseline"},
    )
    assert r.status_code == 200
    r = owner_client.patch(
        f"/api/scenarios/{public_id}",
        json={"description": "second save", "snapshot_note": "refined inputs"},
    )
    assert r.status_code == 200
    r = owner_client.get(f"/api/governance/scenarios/{public_id}/versions")
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) == 2
    notes = [v["note"] for v in versions]
    assert "refined inputs" in notes
    assert "initial baseline" in notes
