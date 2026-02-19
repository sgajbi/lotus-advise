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

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "demo")


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


@pytest.mark.parametrize(
    "filename, expected_status",
    [
        ("10_advisory_proposal_simulate.json", "READY"),
        ("11_advisory_auto_funding_single_ccy.json", "READY"),
        ("12_advisory_partial_funding.json", "READY"),
        ("13_advisory_missing_fx_blocked.json", "BLOCKED"),
        ("14_advisory_drift_asset_class.json", "READY"),
        ("15_advisory_drift_instrument.json", "READY"),
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
