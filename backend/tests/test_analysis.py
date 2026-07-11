"""Analysis & evidence endpoint tests."""

from __future__ import annotations


def _create_scenario(client) -> str:
    body = {
        "name": "Analysis scn",
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


def test_analysis_empty_by_default(owner_client):
    pid = _create_scenario(owner_client)
    r = owner_client.get(f"/api/scenarios/{pid}/analysis")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario_id"] == pid
    assert body["summary"] is None
    assert body["data_sources"] == []
    assert body["assumptions"] == []
    assert body["gaps"] == []
    assert body["input_rationale"] == {}


def test_analysis_upsert_roundtrip(owner_client):
    pid = _create_scenario(owner_client)
    payload = {
        "summary": "Ransomware exposure analysis",
        "confidence": "medium",
        "data_sources": [
            {"title": "Industry DBIR", "reference": "https://example.test", "confidence": "high"}
        ],
        "assumptions": [{"statement": "No EDR on ERP hosts", "impact": "raises vulnerability"}],
        "gaps": [{"description": "No local incident history", "severity": "medium"}],
        "input_rationale": {"tef": "3-5 attempts/yr from IR data", "plm": "  "},
    }
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == "Ransomware exposure analysis"
    assert body["confidence"] == "medium"
    assert len(body["data_sources"]) == 1
    assert body["data_sources"][0]["title"] == "Industry DBIR"
    assert len(body["assumptions"]) == 1
    assert len(body["gaps"]) == 1
    # Blank rationale entries are dropped.
    assert body["input_rationale"] == {"tef": "3-5 attempts/yr from IR data"}
    assert body["updated_at"] is not None

    # Persisted across a fresh GET.
    r2 = owner_client.get(f"/api/scenarios/{pid}/analysis")
    assert r2.json()["summary"] == "Ransomware exposure analysis"


def test_analysis_partial_update_preserves_other_fields(owner_client):
    pid = _create_scenario(owner_client)
    owner_client.put(
        f"/api/scenarios/{pid}/analysis",
        json={"summary": "first", "confidence": "low"},
    )
    # Update only confidence; summary should remain.
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"confidence": "high"})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == "first"
    assert body["confidence"] == "high"


def test_analysis_readonly_cannot_write(owner_client):
    _create_user(owner_client, "ro-analysis@local", "readonly")
    pid = _create_scenario(owner_client)
    owner_client.post("/api/auth/logout")
    owner_client.post(
        "/api/auth/login",
        json={"email": "ro-analysis@local", "password": "TestPass1!"},
    )
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "x"})
    assert r.status_code == 403


def test_analysis_404_for_unknown_scenario(owner_client):
    r = owner_client.get("/api/scenarios/does-not-exist/analysis")
    assert r.status_code == 404


def test_analysis_save_is_audited(owner_client):
    pid = _create_scenario(owner_client)
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "first pass"})
    assert r.status_code == 200
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "revised"})
    assert r.status_code == 200

    r = owner_client.get("/api/governance/audit?limit=50")
    assert r.status_code == 200
    entries = [e for e in r.json() if e["entity_type"] == "scenario.analysis"]
    assert len(entries) == 2, r.text
    # Newest first: the second save is an update, the first was a create.
    assert entries[0]["action"] == "update"
    assert entries[1]["action"] == "create"
    assert "analysis & evidence" in entries[0]["summary"].lower()


def test_analysis_locked_once_approved(owner_client):
    """Evidence backing an approved scenario is part of the approved package."""
    owner_client.patch("/api/settings", json={"enforce_separation_of_duties": False})
    pid = _create_scenario(owner_client)
    owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "pre-approval"})
    owner_client.post(
        f"/api/governance/scenarios/{pid}/transition", json={"action": "submit_for_review"}
    )
    owner_client.post(f"/api/governance/scenarios/{pid}/transition", json={"action": "approve"})

    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "tampered"})
    assert r.status_code == 409, r.text
    # Reads still work; content unchanged.
    assert owner_client.get(f"/api/scenarios/{pid}/analysis").json()["summary"] == "pre-approval"


def test_non_owning_reviewer_cannot_write_analysis(owner_client):
    """Analysis writes follow the same ownership gate as scenario edits."""
    pid = _create_scenario(owner_client)  # owned by the owner account
    _create_user(owner_client, "other-reviewer@local", "reviewer")
    owner_client.post("/api/auth/logout")
    owner_client.post(
        "/api/auth/login",
        json={"email": "other-reviewer@local", "password": "TestPass1!"},
    )
    r = owner_client.put(f"/api/scenarios/{pid}/analysis", json={"summary": "not mine"})
    assert r.status_code == 403


def test_scenario_types_presets_and_custom(owner_client):
    r = owner_client.get("/api/scenario-types")
    assert r.status_code == 200, r.text
    types = r.json()["types"]
    assert "Ransomware" in types
    n = len(types)

    # Add a custom type.
    r = owner_client.post("/api/scenario-types", json={"name": "Quantum Decryption"})
    assert r.status_code == 201, r.text
    types2 = r.json()["types"]
    assert "Quantum Decryption" in types2
    assert len(types2) == n + 1

    # Adding a duplicate (case-insensitive) is a no-op.
    r = owner_client.post("/api/scenario-types", json={"name": "ransomware"})
    assert r.status_code == 201
    assert len(r.json()["types"]) == n + 1
