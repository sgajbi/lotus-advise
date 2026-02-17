"""
FILE: tests/demo/test_demo_scenarios.py
Verifies that the public demo scenarios in docs/demo/ execute correctly.
"""

import json
import os

import pytest

from src.core.engine import run_simulation
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
    ],
)
def test_demo_scenario_execution(filename, expected_status):
    data = load_demo_scenario(filename)

    # Parse inputs using Pydantic models
    portfolio = PortfolioSnapshot(**data["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**data["market_data_snapshot"])
    model = ModelPortfolio(**data["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in data["shelf_entries"]]
    options = EngineOptions(**data.get("options", {}))

    # Run
    result = run_simulation(portfolio, market_data, model, shelf, options)

    # Verify
    assert result.status == expected_status, (
        f"Scenario {filename} failed. Got {result.status}, expected {expected_status}"
    )
