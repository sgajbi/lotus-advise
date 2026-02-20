"""
FILE: tests/demo/test_demo_scenarios.py
Verifies that the public demo scenarios in docs/demo/ execute correctly.
"""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app, get_db_session
from src.core.dpm_engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "demo")


def load_demo_scenario(filename):
    path = os.path.join(DEMO_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    return data


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("01_standard_drift.json", "READY"),
        ("02_sell_to_fund.json", "READY"),
        ("03_multi_currency_fx.json", "READY"),
        ("04_safety_sell_only.json", "PENDING_REVIEW"),
        ("05_safety_hard_block_price.json", "BLOCKED"),
        ("06_tax_aware_hifo.json", "READY"),
        ("07_settlement_overdraft_block.json", "BLOCKED"),
        ("08_solver_mode.json", "READY"),
    ],
)
def test_demo_scenario_execution(filename, expected_status):
    data = load_demo_scenario(filename)

    portfolio = PortfolioSnapshot(**data["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**data["market_data_snapshot"])
    model = ModelPortfolio(**data["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in data["shelf_entries"]]
    options = EngineOptions(**data.get("options", {}))

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status == expected_status, (
        f"Scenario {filename} failed. Got {result.status}, expected {expected_status}"
    )


async def _override_get_db_session():
    yield None


def test_demo_batch_scenario_execution():
    data = load_demo_scenario("09_batch_what_if_analysis.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            response = client.post("/rebalance/analyze", json=data)
        finally:
            app.dependency_overrides = original_overrides

    assert response.status_code == 200
    body = response.json()
    assert set(body["results"].keys()) == {"baseline", "tax_budget", "settlement_guard"}
    assert set(body["comparison_metrics"].keys()) == {"baseline", "tax_budget", "settlement_guard"}
    assert body["failed_scenarios"] == {}


def test_demo_async_batch_scenario_execution():
    data = load_demo_scenario("26_dpm_async_batch_analysis.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            accepted = client.post(
                "/rebalance/analyze/async",
                json=data,
                headers={"X-Correlation-Id": "demo-corr-26-async"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            operation = client.get(f"/rebalance/operations/{operation_id}")
        finally:
            app.dependency_overrides = original_overrides

    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "SUCCEEDED"
    assert operation_body["result"]["warnings"] == ["PARTIAL_BATCH_FAILURE"]
    assert set(operation_body["result"]["failed_scenarios"].keys()) == {"invalid_options"}
    assert set(operation_body["result"]["results"].keys()) == {"baseline"}


def test_demo_dpm_supportability_artifact_flow_via_api():
    data = load_demo_scenario("27_dpm_supportability_artifact_flow.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            simulate = client.post(
                "/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-27-supportability",
                    "X-Correlation-Id": "demo-corr-27-supportability",
                },
            )
            assert simulate.status_code == 200
            run_id = simulate.json()["rebalance_run_id"]

            by_run = client.get(f"/rebalance/runs/{run_id}")
            by_correlation = client.get(
                "/rebalance/runs/by-correlation/demo-corr-27-supportability"
            )
            by_idempotency = client.get("/rebalance/runs/idempotency/demo-27-supportability")
            artifact_one = client.get(f"/rebalance/runs/{run_id}/artifact")
            artifact_two = client.get(f"/rebalance/runs/{run_id}/artifact")
        finally:
            app.dependency_overrides = original_overrides

    assert by_run.status_code == 200
    assert by_correlation.status_code == 200
    assert by_idempotency.status_code == 200
    assert artifact_one.status_code == 200
    assert artifact_two.status_code == 200
    assert by_run.json()["rebalance_run_id"] == run_id
    assert by_correlation.json()["rebalance_run_id"] == run_id
    assert by_idempotency.json()["rebalance_run_id"] == run_id
    assert artifact_one.json()["rebalance_run_id"] == run_id
    assert (
        artifact_one.json()["evidence"]["hashes"]["artifact_hash"]
        == artifact_two.json()["evidence"]["hashes"]["artifact_hash"]
    )


def test_demo_dpm_async_manual_execute_guard_via_api():
    data = load_demo_scenario("28_dpm_async_manual_execute_guard.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            accepted = client.post(
                "/rebalance/analyze/async",
                json=data,
                headers={"X-Correlation-Id": "demo-corr-28-async-inline"},
            )
            assert accepted.status_code == 202
            operation_id = accepted.json()["operation_id"]
            execute = client.post(f"/rebalance/operations/{operation_id}/execute")
        finally:
            app.dependency_overrides = original_overrides

    assert execute.status_code == 409
    assert execute.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_EXECUTABLE"


def test_demo_dpm_idempotency_history_supportability_via_api(monkeypatch):
    data = load_demo_scenario("30_dpm_idempotency_history_supportability.json")
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    monkeypatch.setenv("DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED", "true")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        try:
            first = client.post(
                "/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-30-idem-history",
                    "X-Correlation-Id": "demo-corr-30-idem-history-1",
                },
            )
            assert first.status_code == 200
            first_run = first.json()["rebalance_run_id"]

            data["options"]["single_position_max_weight"] = "0.50"
            second = client.post(
                "/rebalance/simulate",
                json=data,
                headers={
                    "Idempotency-Key": "demo-30-idem-history",
                    "X-Correlation-Id": "demo-corr-30-idem-history-2",
                },
            )
            assert second.status_code == 200
            second_run = second.json()["rebalance_run_id"]

            history = client.get("/rebalance/idempotency/demo-30-idem-history/history")
        finally:
            app.dependency_overrides = original_overrides

    assert history.status_code == 200
    body = history.json()
    assert body["idempotency_key"] == "demo-30-idem-history"
    assert len(body["history"]) == 2
    assert body["history"][0]["rebalance_run_id"] == first_run
    assert body["history"][0]["correlation_id"] == "demo-corr-30-idem-history-1"
    assert body["history"][1]["rebalance_run_id"] == second_run
    assert body["history"][1]["correlation_id"] == "demo-corr-30-idem-history-2"


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("10_advisory_proposal_simulate.json", "READY"),
        ("11_advisory_auto_funding_single_ccy.json", "READY"),
        ("12_advisory_partial_funding.json", "READY"),
        ("13_advisory_missing_fx_blocked.json", "BLOCKED"),
        ("14_advisory_drift_asset_class.json", "READY"),
        ("15_advisory_drift_instrument.json", "READY"),
        ("16_advisory_suitability_resolved_single_position.json", "READY"),
        ("17_advisory_suitability_new_issuer_breach.json", "READY"),
        ("18_advisory_suitability_sell_only_violation.json", "BLOCKED"),
    ],
)
def test_demo_advisory_scenarios_via_api(filename, expected_status):
    data = load_demo_scenario(filename)
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        PROPOSAL_IDEMPOTENCY_CACHE.clear()
        try:
            response = client.post(
                "/rebalance/proposals/simulate",
                json=data,
                headers={"Idempotency-Key": f"demo-{filename}"},
            )
        finally:
            app.dependency_overrides = original_overrides
            PROPOSAL_IDEMPOTENCY_CACHE.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == expected_status

    if filename in {"11_advisory_auto_funding_single_ccy.json", "12_advisory_partial_funding.json"}:
        assert [intent["intent_type"] for intent in body["intents"]] == [
            "FX_SPOT",
            "SECURITY_TRADE",
        ]
        assert body["intents"][1]["dependencies"] == [body["intents"][0]["intent_id"]]
    if filename in {"14_advisory_drift_asset_class.json", "15_advisory_drift_instrument.json"}:
        assert "drift_analysis" in body
    if filename in {
        "16_advisory_suitability_resolved_single_position.json",
        "17_advisory_suitability_new_issuer_breach.json",
        "18_advisory_suitability_sell_only_violation.json",
    }:
        assert "suitability" in body


def test_demo_advisory_artifact_scenario_via_api():
    data = load_demo_scenario("19_advisory_proposal_artifact.json")
    with TestClient(app) as client:
        original_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db_session] = _override_get_db_session
        PROPOSAL_IDEMPOTENCY_CACHE.clear()
        try:
            response = client.post(
                "/rebalance/proposals/artifact",
                json=data,
                headers={"Idempotency-Key": "demo-19-advisory-artifact"},
            )
        finally:
            app.dependency_overrides = original_overrides
            PROPOSAL_IDEMPOTENCY_CACHE.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "READY"
    assert body["summary"]["recommended_next_step"] == "CLIENT_CONSENT"
    assert body["trades_and_funding"]["trade_list"]
    assert body["evidence_bundle"]["hashes"]["artifact_hash"].startswith("sha256:")
