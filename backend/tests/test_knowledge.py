"""Knowledge library tests."""

from __future__ import annotations


def test_seeded_threats_present(owner_client):
    r = owner_client.get("/api/knowledge/threats")
    assert r.status_code == 200, r.text
    body = r.json()
    names = {t["name"] for t in body}
    assert "Cybercriminals" in names
    assert "Phishing" in names  # MITRE T1566
    assert "Data Encrypted for Impact (Ransomware)" in names


def test_seeded_controls_present(owner_client):
    r = owner_client.get("/api/knowledge/controls?framework=NIST CSF 2.0")
    assert r.status_code == 200
    csf = r.json()
    codes = {c["code"] for c in csf}
    assert {"GV", "ID", "PR", "DE", "RS", "RC"} <= codes

    r = owner_client.get("/api/knowledge/controls?framework=CIS Controls v8.1")
    assert r.status_code == 200
    cis = r.json()
    assert len(cis) == 18


def test_seeded_benchmarks(owner_client):
    r = owner_client.get("/api/knowledge/benchmarks")
    assert r.status_code == 200
    body = r.json()
    assert any(b["industry"] == "Manufacturing" for b in body)
    # benchmark distribution shape is valid for the simulation engine
    for b in body:
        d = b["distribution"]
        assert "type" in d


def test_threat_search(owner_client):
    r = owner_client.get("/api/knowledge/threats?q=ransomware")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert any("Ransomware" in n for n in names)


def test_import_custom_threats(owner_client):
    import io
    import json

    payload = json.dumps(
        [
            {
                "public_id": "user-threat-001",
                "name": "Custom adversary",
                "category": "Custom",
                "description": "Imported via API",
                "references": [],
            }
        ]
    ).encode()
    r = owner_client.post(
        "/api/knowledge/import?kind=threats&source=my-team",
        files={"file": ("threats.json", io.BytesIO(payload), "application/json")},
    )
    assert r.status_code == 201, r.text
    r = owner_client.get("/api/knowledge/threats?q=custom")
    names = [t["name"] for t in r.json()]
    assert "Custom adversary" in names
