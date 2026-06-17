from src.core.advisory.simulation_intent_plan import build_simulation_intent_plan
from src.core.common.diagnostics import make_diagnostics_data
from src.core.models import EngineOptions
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    portfolio_snapshot,
    position,
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


def test_simulation_intent_plan_records_negative_cash_withdrawal_hard_failure():
    diagnostics = make_diagnostics_data()

    plan = build_simulation_intent_plan(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_intent_plan_negative_cash",
            base_currency="USD",
            positions=[],
            cash_balances=[cash("USD", "100")],
        ),
        market_data=market_data_snapshot(prices=[]),
        shelf=[],
        options=EngineOptions(
            enable_proposal_simulation=True,
            proposal_block_negative_cash=True,
        ),
        proposed_cash_flows=[
            {"currency": "USD", "amount": "-150", "description": "Client withdrawal"},
        ],
        proposed_trades=[],
        diagnostics=diagnostics,
    )

    assert [intent.intent_type for intent in plan.intents] == ["CASH_FLOW"]
    assert plan.intents[0].intent_id == "oi_cf_1"
    assert plan.hard_failures == ["PROPOSAL_WITHDRAWAL_NEGATIVE_CASH"]
    assert diagnostics.warnings == ["PROPOSAL_WITHDRAWAL_NEGATIVE_CASH"]
    assert plan.after_portfolio.cash_balances[0].amount == -50


def test_simulation_intent_plan_orders_mixed_intents_and_applies_after_state():
    diagnostics = make_diagnostics_data()

    plan = build_simulation_intent_plan(
        portfolio=portfolio_snapshot(
            portfolio_id="pf_intent_plan_mixed",
            base_currency="USD",
            positions=[position("EQ_SELL", "5")],
            cash_balances=[cash("USD", "1000")],
        ),
        market_data=market_data_snapshot(
            prices=[
                price("EQ_SELL", "50", "USD"),
                price("EQ_BUY", "100", "USD"),
            ]
        ),
        shelf=[
            shelf_entry("EQ_SELL"),
            shelf_entry("EQ_BUY"),
        ],
        options=EngineOptions(
            enable_proposal_simulation=True,
            link_buy_to_same_currency_sell_dependency=True,
        ),
        proposed_cash_flows=[
            {"currency": "USD", "amount": "200", "description": "Client top-up"},
        ],
        proposed_trades=[
            {"side": "SELL", "instrument_id": "EQ_SELL", "quantity": "2"},
            {"side": "BUY", "instrument_id": "EQ_BUY", "quantity": "3"},
        ],
        diagnostics=diagnostics,
    )

    assert [intent.intent_type for intent in plan.intents] == [
        "CASH_FLOW",
        "SECURITY_TRADE",
        "SECURITY_TRADE",
    ]
    assert [intent.intent_id for intent in plan.intents] == ["oi_cf_1", "oi_1", "oi_2"]
    assert plan.intents[1].side == "SELL"
    assert plan.intents[2].side == "BUY"
    assert plan.intents[2].dependencies == ["oi_1"]
    assert {
        position.instrument_id: position.quantity for position in plan.after_portfolio.positions
    } == {
        "EQ_SELL": 3,
        "EQ_BUY": 3,
    }
    assert {cash.currency: cash.amount for cash in plan.after_portfolio.cash_balances} == {
        "USD": 1000,
    }
    assert plan.hard_failures == []
    assert diagnostics.warnings == []
