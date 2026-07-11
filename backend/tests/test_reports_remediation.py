"""Tests covering the fix.md §6 + §7 remediation work."""

from __future__ import annotations

import zipfile
from io import BytesIO


def _make_scenario(client, name: str = "Remediation scn") -> str:
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
        json={"iterations": 5_000, "seed": 11, "persist_artifacts": True},
    )
    assert r.status_code == 201
    return public_id


# -------------------------------------------------------- §6 select none


def test_empty_scenario_list_is_rejected(owner_client):
    _make_scenario(owner_client)
    # Explicit empty list — different from None — must be a 400, not "all".
    r = owner_client.post(
        "/api/reports/html",
        json={"kind": "executive", "scope": "portfolio", "scenario_ids": []},
    )
    assert r.status_code == 400, r.text
    assert "at least one scenario" in r.text.lower()


def test_null_scenario_list_means_all(owner_client):
    _make_scenario(owner_client, "Scenario A")
    _make_scenario(owner_client, "Scenario B")
    r = owner_client.post(
        "/api/reports/html",
        json={"kind": "executive", "scope": "portfolio", "scenario_ids": None},
    )
    assert r.status_code == 200
    assert "Scenario A" in r.text or "FORLAS CRQ" in r.text


def test_specific_scenarios_renders_only_those(owner_client):
    a = _make_scenario(owner_client, "Selected scenario")
    _make_scenario(owner_client, "Other scenario")
    r = owner_client.post(
        "/api/reports/html",
        json={"kind": "board", "scope": "both", "scenario_ids": [a]},
    )
    assert r.status_code == 200
    assert "Selected scenario" in r.text
    assert "Other scenario" not in r.text


# -------------------------------------------------------- §7 DOCX completeness


def test_docx_includes_all_thirteen_sections(owner_client):
    _make_scenario(owner_client, "Section coverage scn")
    r = owner_client.post(
        "/api/reports/docx",
        json={"kind": "board", "scope": "both"},
    )
    assert r.status_code == 200
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    expected = [
        "Executive Summary",
        "Scenario Overview",
        "FAIR Inputs",
        "Monte Carlo Results",
        "Percentiles",
        "Loss Exceedance Curve",
        "Risk Metrics",
        "Tables — Per-Scenario Summary",
        "Charts",
        "Assumptions",
        "Knowledge References",
        "Recommendations",
        "Appendix",
    ]
    for section in expected:
        assert section in xml, f"DOCX missing section: {section}"


def test_docx_uses_aud_prefix_not_usd(owner_client):
    _make_scenario(owner_client)
    r = owner_client.post("/api/reports/docx", json={"kind": "executive"})
    assert r.status_code == 200
    with zipfile.ZipFile(BytesIO(r.content)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    assert "A$" in xml
    assert "USD" not in xml
    assert "US$" not in xml


def test_html_uses_aud_prefix(owner_client):
    import re

    _make_scenario(owner_client)
    r = owner_client.post("/api/reports/html", json={"kind": "executive"})
    assert r.status_code == 200
    # Strip inlined data URIs (e.g. the base64 brand logo) before checking for
    # stray currency labels — random base64 can contain "USD" by chance.
    visible = re.sub(r"data:[^\"']+", "", r.text)
    assert "A$" in visible
    assert "USD" not in visible
    assert "US$" not in visible
