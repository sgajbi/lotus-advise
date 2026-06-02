from src.core.advisory.simulation_intent_plan import build_simulation_intent_plan
from src.core.common.diagnostics import make_diagnostics_data
from src.core.models import EngineOptions
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    portfolio_snapshot,
    price,
    shelf_entry,
)


def test_simulation_intent_plan_blocks_restricted_buy_without_override():
    diagnostics = make_diagnostics_data()

    plan = build_simulation_intent_plan(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_intent_plan_restricted",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "1000")],
        ),
        market_data=market_data_snapshot(prices=[price("EQ_RESTRICTED", "100", "USD")]),
        shelf=[shelf_entry("EQ_RESTRICTED", status="RESTRICTED")],
        options=EngineOptions(enable_proposal_simulation=True, allow_restricted=False),
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_RESTRICTED", "quantity": "1"}],
        diagnostics=diagnostics,
    )

    assert plan.intents == []
    assert plan.hard_failures == ["PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF"]
    assert diagnostics.warnings == ["PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF"]


def test_simulation_intent_plan_records_missing_shelf_without_execution_intent():
    diagnostics = make_diagnostics_data()

    plan = build_simulation_intent_plan(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_intent_plan_missing_shelf",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "1000")],
        ),
        market_data=market_data_snapshot(prices=[price("EQ_MISSING", "100", "USD")]),
        shelf=[],
        options=EngineOptions(enable_proposal_simulation=True),
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_MISSING", "quantity": "1"}],
        diagnostics=diagnostics,
    )

    assert plan.intents == []
    assert plan.hard_failures == []
    assert diagnostics.data_quality["shelf_missing"] == ["EQ_MISSING"]
