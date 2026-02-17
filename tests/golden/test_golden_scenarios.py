"""
FILE: tests/golden/test_golden_scenarios.py
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

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "..", "golden_data")


def load_golden_scenarios():
    scenarios = []
    for filepath in glob.glob(os.path.join(GOLDEN_DIR, "*.json")):
        with open(filepath, "r") as f:
            data = json.load(f)
            scenarios.append((os.path.basename(filepath), data))
    return scenarios


def _normalized_actual_intent(intent):
    base = {"intent_type": intent.intent_type}
    if intent.intent_type == "SECURITY_TRADE":
        base.update(
            {
                "instrument_id": intent.instrument_id,
                "side": intent.side,
                "quantity": str(intent.quantity),
            }
        )
    elif intent.intent_type == "FX_SPOT":
        base.update(
            {
                "pair": intent.pair,
                "buy_currency": intent.buy_currency,
                "sell_currency": intent.sell_currency,
            }
        )
    return base


def _normalized_expected_intent(intent):
    base = {"intent_type": intent["intent_type"]}
    if intent["intent_type"] == "SECURITY_TRADE":
        base.update(
            {
                "instrument_id": intent["instrument_id"],
                "side": intent["side"],
                "quantity": str(intent["quantity"]),
            }
        )
    elif intent["intent_type"] == "FX_SPOT":
        base.update(
            {
                "pair": intent["pair"],
                "buy_currency": intent["buy_currency"],
                "sell_currency": intent["sell_currency"],
            }
        )
    return base


def _intent_sort_key(intent):
    return (
        intent["intent_type"],
        intent.get("instrument_id", ""),
        intent.get("pair", ""),
        intent.get("side", ""),
        intent.get("buy_currency", ""),
        intent.get("sell_currency", ""),
        intent.get("quantity", ""),
    )


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

        actual_intents = sorted(
            (_normalized_actual_intent(i) for i in result.intents),
            key=_intent_sort_key,
        )
        expected_intents = sorted(
            (_normalized_expected_intent(i) for i in expected["intents"]),
            key=_intent_sort_key,
        )
        assert actual_intents == expected_intents

        # Validate After-State Cash (High level check)
        act_cash = {c.currency: c.amount for c in result.after_simulated.cash_balances}
        for exp_c in expected["after_simulated"]["cash_balances"]:
            ccy = exp_c["currency"]
            amt = Decimal(str(exp_c["amount"]))
            # Allow small float diffs from JSON serialization if strictly needed,
            # but Pydantic should handle this. Exact match preferred.
            assert abs(act_cash.get(ccy, Decimal(0)) - amt) < Decimal("0.0001")
