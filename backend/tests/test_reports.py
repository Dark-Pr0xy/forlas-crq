"""Report rendering tests — HTML + DOCX."""

from __future__ import annotations

import zipfile
from io import BytesIO


def _create_and_simulate(client, name: str = "Report scn") -> str:
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
    public_id = r.json()["id"]
    r = client.post(
        f"/api/scenarios/{public_id}/simulations",
        json={"iterations": 5_000, "seed": 9, "persist_artifacts": True},
    )
    assert r.status_code == 201, r.text
    return public_id


def test_html_executive_renders(owner_client):
    _create_and_simulate(owner_client)
    r = owner_client.post(
        "/api/reports/html",
        json={"kind": "executive", "scope": "portfolio"},
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "Executive Summary" in body
    assert "Portfolio summary" in body
    assert "FORLAS CRQ" in body
    assert "<html" in body.lower()


def test_html_board_renders(owner_client):
    _create_and_simulate(owner_client, "Board scn")
    r = owner_client.post(
        "/api/reports/html",
        json={"kind": "board", "scope": "both"},
    )
    assert r.status_code == 200
    assert "Board Pack" in r.text
    assert "Per-scenario detail" in r.text
    assert "Board scn" in r.text


def test_docx_executive_download(owner_client):
    _create_and_simulate(owner_client)
    r = owner_client.post(
        "/api/reports/docx",
        json={"kind": "executive"},
    )
    assert r.status_code == 200, r.text
    assert (
        r.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    # A valid .docx is a ZIP that contains `word/document.xml`
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names


def test_docx_board_includes_scenarios(owner_client):
    public_id = _create_and_simulate(owner_client, "Docx board scn")
    r = owner_client.post(
        "/api/reports/docx",
        json={"kind": "board", "scenario_ids": [public_id]},
    )
    assert r.status_code == 200
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
        assert "Docx board scn" in xml
