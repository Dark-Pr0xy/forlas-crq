"""CRUD tests for the knowledge library (fix.md §5)."""

from __future__ import annotations


def test_builtin_threat_can_be_edited(owner_client):
    """Built-in entries are editable; the seeder is idempotent on public_id
    so the user's edit persists across restarts."""
    listed = owner_client.get("/api/knowledge/threats").json()
    builtin = next(t for t in listed if t["source"] == "builtin")
    r = owner_client.patch(
        f"/api/knowledge/threats/{builtin['id']}",
        json={
            "name": f"{builtin['name']} (locally tailored)",
            "category": builtin.get("category") or "Custom",
            "description": "Updated description",
            "references": [],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"].endswith("(locally tailored)")


def test_builtin_threat_can_be_deleted(owner_client):
    """Built-in deletion removes the row from this DB. The bootstrap seeder
    re-creates the original on next startup, which is the intended reset path."""
    listed = owner_client.get("/api/knowledge/threats").json()
    builtin = next(t for t in listed if t["source"] == "builtin")
    r = owner_client.delete(f"/api/knowledge/threats/{builtin['id']}")
    assert r.status_code == 200
    # And it's gone from this DB
    r = owner_client.get("/api/knowledge/threats")
    assert all(t["id"] != builtin["id"] for t in r.json())


def test_user_threat_full_crud(owner_client):
    r = owner_client.post(
        "/api/knowledge/threats",
        json={
            "name": "Custom adversary",
            "category": "Custom",
            "description": "Inline test",
            "references": ["https://example.com"],
        },
    )
    assert r.status_code == 201, r.text
    threat = r.json()
    assert threat["source"] == "user"
    threat_id = threat["id"]

    r = owner_client.patch(
        f"/api/knowledge/threats/{threat_id}",
        json={
            "name": "Custom adversary v2",
            "category": "Custom",
            "description": "Updated",
            "references": [],
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Custom adversary v2"

    r = owner_client.delete(f"/api/knowledge/threats/{threat_id}")
    assert r.status_code == 200

    r = owner_client.get(f"/api/knowledge/threats")
    assert all(t["id"] != threat_id for t in r.json())


def test_user_control_crud(owner_client):
    r = owner_client.post(
        "/api/knowledge/controls",
        json={
            "framework": "Custom Framework",
            "code": "CUS-1",
            "name": "Custom control",
            "description": "test",
            "category": "Test",
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    r = owner_client.patch(
        f"/api/knowledge/controls/{cid}",
        json={
            "framework": "Custom Framework",
            "code": "CUS-1",
            "name": "Renamed",
            "description": None,
            "category": "Test",
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"

    r = owner_client.delete(f"/api/knowledge/controls/{cid}")
    assert r.status_code == 200


def test_user_benchmark_crud(owner_client):
    r = owner_client.post(
        "/api/knowledge/benchmarks",
        json={
            "name": "Custom benchmark",
            "industry": "Custom",
            "metric": "tef",
            "distribution": {"type": "pert", "min": 1, "mode": 4, "max": 12},
            "citation": "n/a",
        },
    )
    assert r.status_code == 201, r.text
    bid = r.json()["id"]

    r = owner_client.patch(
        f"/api/knowledge/benchmarks/{bid}",
        json={
            "name": "Renamed",
            "industry": "Custom",
            "metric": "tef",
            "distribution": {"type": "pert", "min": 1, "mode": 5, "max": 12},
            "citation": "n/a",
        },
    )
    assert r.status_code == 200
    assert r.json()["distribution"]["mode"] == 5

    r = owner_client.delete(f"/api/knowledge/benchmarks/{bid}")
    assert r.status_code == 200
