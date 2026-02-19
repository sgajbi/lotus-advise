import json
import os
from decimal import Decimal

from src.core.engine import run_proposal_simulation
from src.core.models import EngineOptions, MarketDataSnapshot, PortfolioSnapshot, ShelfEntry


def test_golden_proposal_14a_advisory_manual_trade_cashflow():
    path = os.path.join(
        os.path.dirname(__file__),
        "../golden_data/scenario_14A_advisory_manual_trade_cashflow.json",
    )
    with open(path, "r") as file:
        data = json.loads(file.read(), parse_float=Decimal)

    inputs = data["proposal_inputs"]
    expected = data["expected_proposal_output"]

    result = run_proposal_simulation(
        portfolio=PortfolioSnapshot(**inputs["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**inputs["market_data_snapshot"]),
        shelf=[ShelfEntry(**entry) for entry in inputs["shelf_entries"]],
        options=EngineOptions(**inputs["options"]),
        proposed_cash_flows=inputs["proposed_cash_flows"],
        proposed_trades=inputs["proposed_trades"],
        request_hash="golden_proposal_test",
    )

    assert result.status == expected["status"]

    assert result.intents[0].intent_type == expected["intents"][0]["intent_type"]
    assert result.intents[0].currency == expected["intents"][0]["currency"]
    assert result.intents[0].amount == Decimal(expected["intents"][0]["amount"])
    assert result.intents[1].intent_type == expected["intents"][1]["intent_type"]
    assert result.intents[1].side == expected["intents"][1]["side"]
    assert result.intents[1].instrument_id == expected["intents"][1]["instrument_id"]
    assert result.intents[1].quantity == Decimal(expected["intents"][1]["quantity"])
    assert result.intents[1].notional.amount == Decimal(
        expected["intents"][1]["notional"]["amount"]
    )
    assert result.intents[1].notional.currency == expected["intents"][1]["notional"]["currency"]

    cash_by_currency = {cash.currency: cash.amount for cash in result.after_simulated.cash_balances}
    assert cash_by_currency["SGD"] == Decimal("13500")

    positions_by_id = {
        position.instrument_id: position.quantity for position in result.after_simulated.positions
    }
    assert positions_by_id["SG_BOND_ETF"] == Decimal("100")
    assert positions_by_id["US_EQ_ETF"] == Decimal("10")
