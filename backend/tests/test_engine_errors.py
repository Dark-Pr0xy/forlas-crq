"""Engine input-error mapping to 422 + Alpha import validation (CODE_REVIEW C4)."""

from __future__ import annotations

import io
import json

import pytest

from app.engine import run_simulation
from app.engine.errors import SimulationInputError
from app.engine.simulation import RunOptions


def test_missing_input_raises_input_error():
    scenario = {"mode": "tef-vuln", "inputs": {"tef": {"type": "pert", "min": 1, "mode": 4, "max": 10}}}
    with pytest.raises(SimulationInputError) as exc:
        run_simulation(scenario, RunOptions(iterations=1000, seed=1))
    # Names the offending variables so the message is actionable.
    assert "plm" in str(exc.value)


def test_bad_bounds_raises_input_error():
    scenario = {
        "mode": "tef-vuln",
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 10, "max": 5},  # mode > max
            "vuln": {"type": "pert", "min": 0, "mode": 0.5, "max": 1},
            "plm": {"type": "pert", "min": 1, "mode": 2, "max": 3},
            "slp_prob": {"type": "pert", "min": 0, "mode": 0.5, "max": 1},
            "slm": {"type": "pert", "min": 1, "mode": 2, "max": 3},
        },
    }
    with pytest.raises(SimulationInputError):
        run_simulation(scenario, RunOptions(iterations=1000, seed=1))


def test_unknown_mode_raises_input_error():
    with pytest.raises(SimulationInputError):
        run_simulation({"mode": "nonsense", "inputs": {}}, RunOptions(iterations=1000, seed=1))


# ---------------------------------------------------------------- API mapping


def _create_valid(client) -> str:
    body = {
        "name": "OK scn",
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


def test_import_skips_invalid_and_reports_count(owner_client):
    payload = json.dumps(
        {
            "scenarios": [
                {"name": "Empty", "mode": "tef-vuln", "inputs": {}},  # invalid
                {
                    "name": "Good",
                    "mode": "tef-vuln",
                    "inputs": {
                        "tef": {"type": "pert", "min": 1, "mode": 4, "max": 10},
                        "vuln": {"type": "pert", "min": 0.05, "mode": 0.25, "max": 0.6},
                        "plm": {"type": "pert", "min": 50000, "mode": 250000, "max": 1500000},
                        "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
                        "slm": {"type": "pert", "min": 25000, "mode": 150000, "max": 2000000},
                    },
                },
            ]
        }
    ).encode()
    r = owner_client.post(
        "/api/import/alpha",
        files={"file": ("alpha.json", io.BytesIO(payload), "application/json")},
    )
    assert r.status_code == 201, r.text
    msg = r.json()["message"]
    assert "Imported 1" in msg
    assert "skipped 1" in msg
    # The valid one is queryable; the invalid one was never stored.
    names = [s["name"] for s in owner_client.get("/api/scenarios").json()]
    assert "Good" in names
    assert "Empty" not in names
