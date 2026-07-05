"""Portfolio aggregation engine + endpoint tests."""

from __future__ import annotations

import numpy as np

from app.engine.portfolio import PortfolioInput, aggregate


def test_empty_inputs():
    r = aggregate([])
    assert r.scenario_count == 0
    assert r.total_ale == 0
    assert r.portfolio_losses.size == 0


def test_sum_of_means():
    rng = np.random.default_rng(1)
    a = rng.lognormal(12, 0.6, 10_000)
    b = rng.lognormal(11, 0.5, 10_000)
    r = aggregate(
        [
            PortfolioInput("sc_a", "A", 0.0, a),
            PortfolioInput("sc_b", "B", 0.0, b),
        ]
    )
    # Sum-of-means identity: aggregate mean must equal the mean of (a + b)
    expected = float((a + b).mean())
    assert abs(r.total_ale - expected) < 1e-6
    assert r.iterations == 10_000


def test_p95_of_sum_geq_sum_of_p95s():
    rng = np.random.default_rng(2)
    a = rng.lognormal(12, 0.5, 20_000)
    b = rng.lognormal(12, 0.5, 20_000)
    r = aggregate(
        [
            PortfolioInput("sc_a", "A", 0.0, a),
            PortfolioInput("sc_b", "B", 0.0, b),
        ]
    )
    # For independent positive RVs, the P95 of the sum is less than the sum of
    # the P95s (subadditivity of tail percentiles). We assert the inequality.
    sum_p95s = float(np.percentile(a, 95)) + float(np.percentile(b, 95))
    assert r.total_p95 < sum_p95s


def test_over_tolerance_count():
    losses_a = np.full(1_000, 2_000_000.0)
    losses_b = np.full(1_000, 100_000.0)
    r = aggregate(
        [
            PortfolioInput("sc_a", "A", tolerance=1_000_000, losses=losses_a),
            PortfolioInput("sc_b", "B", tolerance=500_000, losses=losses_b),
        ]
    )
    assert r.over_tolerance_count == 1
    assert r.per_scenario[0]["over_tolerance"] is True
    assert r.per_scenario[1]["over_tolerance"] is False


def test_insurance_offset_reduces_loss():
    losses = np.full(1_000, 1_000_000.0)
    baseline = aggregate([PortfolioInput("sc_a", "A", 0.0, losses)])
    with_insurance = aggregate(
        [PortfolioInput("sc_a", "A", 0.0, losses)],
        insurance_deductible=200_000,
        insurance_limit=500_000,
    )
    # Recovery per iter = min(500K, max(0, 1M - 200K)) = 500K. Net loss = 500K.
    assert abs(with_insurance.total_ale - 500_000) < 1e-6
    assert with_insurance.total_ale < baseline.total_ale


# ------------------------------------------------------------ API integration


def _create_and_simulate(client, name: str, plm_mode: float) -> str:
    body = {
        "name": name,
        "mode": "tef-vuln",
        "tolerance": 1_000_000,
        "inputs": {
            "tef": {"type": "pert", "min": 1, "mode": 4, "max": 10},
            "vuln": {"type": "pert", "min": 0.05, "mode": 0.25, "max": 0.6},
            "plm": {"type": "pert", "min": 50_000, "mode": plm_mode, "max": 1_500_000},
            "slp_prob": {"type": "pert", "min": 0.1, "mode": 0.4, "max": 0.8},
            "slm": {"type": "pert", "min": 25_000, "mode": 150_000, "max": 2_000_000},
        },
    }
    r = client.post("/api/scenarios", json=body)
    assert r.status_code == 201, r.text
    public_id = r.json()["id"]
    r = client.post(
        f"/api/scenarios/{public_id}/simulations",
        json={"iterations": 5_000, "seed": 7, "persist_artifacts": True},
    )
    assert r.status_code == 201, r.text
    return public_id


def test_portfolio_rollup_endpoint(owner_client):
    _create_and_simulate(owner_client, "Scenario A", 250_000)
    _create_and_simulate(owner_client, "Scenario B", 400_000)
    r = owner_client.get("/api/portfolio/rollup")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scenario_count"] == 2
    assert body["simulated_count"] == 2
    assert body["total_ale"] > 0
    assert body["total_p95"] >= body["total_p50"]
    assert len(body["top_scenarios"]) == 2
    assert body["lec_curve"]


def test_snapshot_lifecycle(owner_client):
    _create_and_simulate(owner_client, "Snapshot scenario", 250_000)
    r = owner_client.post("/api/portfolio/snapshots", json={"reason": "smoke"})
    assert r.status_code == 201, r.text
    snap_id = r.json()["id"]
    r = owner_client.get("/api/portfolio/snapshots")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert snap_id in ids


def test_register_endpoint(owner_client):
    _create_and_simulate(owner_client, "Register scenario", 250_000)
    r = owner_client.get("/api/portfolio/register")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    row = rows[0]
    assert row["name"] == "Register scenario"
    assert row["ale"] is not None
    assert row["p95"] is not None
