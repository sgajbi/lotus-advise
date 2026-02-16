"""
FILE: tests/test_golden_scenarios.py
"""

import glob
import json
import os
from decimal import Decimal

import pytest

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    PortfolioSnapshot,
    ShelfEntry,
)

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden_data")


def load_golden_scenarios():
    scenarios = []
    for filepath in glob.glob(os.path.join(GOLDEN_DIR, "*.json")):
        with open(filepath, "r") as f:
            data = json.load(f)
            scenarios.append((os.path.basename(filepath), data))
    return scenarios


@pytest.mark.parametrize("filename, scenario", load_golden_scenarios())
def test_golden_scenario(filename, scenario):
    inputs = scenario["inputs"]
    portfolio = PortfolioSnapshot(**inputs["portfolio_snapshot"])
    market_data = MarketDataSnapshot(**inputs["market_data_snapshot"])
    model = ModelPortfolio(**inputs["model_portfolio"])
    shelf = [ShelfEntry(**s) for s in inputs["shelf_entries"]]

    # Handle optional fields in options that might be missing in old goldens
    opt_dict = inputs["options"]
    options = EngineOptions(**opt_dict)

    if "error" in scenario["expected_outputs"]:
        with pytest.raises(ValueError, match=scenario["expected_outputs"]["error"]):
            run_simulation(portfolio, market_data, model, shelf, options)
    else:
        result = run_simulation(portfolio, market_data, model, shelf, options)
        expected = scenario["expected_outputs"]

        assert result.status == expected["status"]
        assert len(result.intents) == len(expected["intents"])

        for act_intent, exp_intent in zip(result.intents, expected["intents"]):
            # RFC-0007A: Strict Type Checking
            assert act_intent.intent_type == exp_intent["intent_type"]

            if act_intent.intent_type == "SECURITY_TRADE":
                assert act_intent.instrument_id == exp_intent["instrument_id"]
                assert act_intent.side == exp_intent["side"]
                # Compare as strings to avoid Decimal precision issues in JSON
                assert str(act_intent.quantity) == str(exp_intent["quantity"])

            elif act_intent.intent_type == "FX_SPOT":
                assert act_intent.pair == exp_intent["pair"]
                assert act_intent.buy_currency == exp_intent["buy_currency"]
                assert act_intent.sell_currency == exp_intent["sell_currency"]

        # Validate After-State Cash (High level check)
        act_cash = {c.currency: c.amount for c in result.after_simulated.cash_balances}
        for exp_c in expected["after_simulated"]["cash_balances"]:
            ccy = exp_c["currency"]
            amt = Decimal(str(exp_c["amount"]))
            # Allow small float diffs from JSON serialization if strictly needed,
            # but Pydantic should handle this. Exact match preferred.
            assert abs(act_cash.get(ccy, Decimal(0)) - amt) < Decimal("0.0001")
