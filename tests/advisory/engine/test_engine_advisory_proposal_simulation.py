from decimal import Decimal

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import EngineOptions
from tests.factories import (
    cash,
    market_data_snapshot,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
)


def _intent_types(result):
    return [intent.intent_type for intent in result.intents]


def test_proposal_simulation_generates_fx_funding_and_dependency():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_1",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "10000")],
    )
    market_data = market_data_snapshot(
        prices=[price("US_EQ", "100", "USD")],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    shelf = [shelf_entry("US_EQ", status="APPROVED")]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "50"}],
        request_hash="proposal_hash_fx_dep",
    )

    assert result.status == "READY"
    assert _intent_types(result) == ["FX_SPOT", "SECURITY_TRADE"]
    fx_intent = result.intents[0]
    buy_intent = result.intents[1]
    assert fx_intent.pair == "USD/SGD"
    assert fx_intent.buy_amount == Decimal("5000.00")
    assert fx_intent.sell_amount_estimated == Decimal("6750.00")
    assert buy_intent.dependencies == [fx_intent.intent_id]


def test_proposal_simulation_supports_partial_funding_with_existing_foreign_cash():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_2",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "10000"), cash("USD", "500")],
    )
    market_data = market_data_snapshot(
        prices=[price("US_EQ", "100", "USD")],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    shelf = [shelf_entry("US_EQ", status="APPROVED")]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "10"}],
        request_hash="proposal_hash_partial_fx",
    )

    assert result.status == "READY"
    assert _intent_types(result) == ["FX_SPOT", "SECURITY_TRADE"]
    fx_intent = result.intents[0]
    assert fx_intent.buy_amount == Decimal("500.00")
    assert fx_intent.sell_amount_estimated == Decimal("675.00")

    usd_cash = next(c for c in result.after_simulated.cash_balances if c.currency == "USD")
    assert usd_cash.amount == Decimal("0.00")
    assert result.diagnostics.funding_plan[0].fx_needed == Decimal("500.00")


def test_proposal_simulation_skips_fx_when_foreign_cash_already_sufficient():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_3",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "1000"), cash("USD", "1000")],
    )
    market_data = market_data_snapshot(
        prices=[price("US_EQ", "100", "USD")],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    shelf = [shelf_entry("US_EQ", status="APPROVED")]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "5"}],
        request_hash="proposal_hash_no_fx_needed",
    )

    assert result.status == "READY"
    assert _intent_types(result) == ["SECURITY_TRADE"]
    buy_intent = result.intents[0]
    assert buy_intent.dependencies == []


def test_proposal_simulation_orders_intents_cashflow_sell_fx_buy():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_4",
        base_currency="SGD",
        positions=[position("US_OLD", "10")],
        cash_balances=[cash("SGD", "1000")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("US_OLD", "100", "USD"),
            price("US_NEW", "100", "USD"),
        ],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    shelf = [
        shelf_entry("US_OLD", status="APPROVED"),
        shelf_entry("US_NEW", status="APPROVED"),
    ]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[{"currency": "SGD", "amount": "3000"}],
        proposed_trades=[
            {"side": "BUY", "instrument_id": "US_NEW", "quantity": "20"},
            {"side": "SELL", "instrument_id": "US_OLD", "quantity": "5"},
        ],
        request_hash="proposal_hash_ordering",
    )

    assert result.status == "READY"
    assert _intent_types(result) == ["CASH_FLOW", "SECURITY_TRADE", "FX_SPOT", "SECURITY_TRADE"]
    assert result.intents[1].side == "SELL"
    assert result.intents[2].intent_type == "FX_SPOT"
    assert result.intents[3].side == "BUY"


def test_proposal_simulation_blocks_missing_fx_for_funding_when_blocking_enabled():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_5",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "10000")],
    )
    market_data = market_data_snapshot(prices=[price("US_EQ", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True, block_on_missing_fx=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("US_EQ", status="APPROVED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "1"}],
        request_hash="proposal_hash_missing_fx_block",
    )

    assert result.status == "BLOCKED"
    assert "USD/SGD" in result.diagnostics.missing_fx_pairs
    assert any(
        rule.reason_code == "PROPOSAL_MISSING_FX_FOR_FUNDING" for rule in result.rule_results
    )


def test_proposal_simulation_marks_pending_review_on_missing_fx_when_non_blocking():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_6",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "10000")],
    )
    market_data = market_data_snapshot(prices=[price("US_EQ", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True, block_on_missing_fx=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("US_EQ", status="APPROVED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "1"}],
        request_hash="proposal_hash_missing_fx_pending",
    )

    assert result.status == "PENDING_REVIEW"
    assert "USD/SGD" in result.diagnostics.missing_fx_pairs
    assert _intent_types(result) == []


def test_proposal_simulation_blocks_when_funding_cash_insufficient():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_fx_7",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "100")],
    )
    market_data = market_data_snapshot(
        prices=[price("US_EQ", "100", "USD")],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("US_EQ", status="APPROVED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "2"}],
        request_hash="proposal_hash_insufficient_cash",
    )

    assert result.status == "BLOCKED"
    assert result.diagnostics.insufficient_cash
    assert any(
        rule.reason_code == "PROPOSAL_INSUFFICIENT_FUNDING_CASH" for rule in result.rule_results
    )


def test_proposal_simulation_blocks_notional_currency_mismatch():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_5b",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("EQ_1", status="APPROVED")]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[
            {
                "side": "BUY",
                "instrument_id": "EQ_1",
                "notional": {"amount": "200", "currency": "EUR"},
            }
        ],
        request_hash="proposal_hash_notional_currency_mismatch",
    )

    assert result.status == "BLOCKED"
    assert result.intents == []
    assert "PROPOSAL_INVALID_TRADE_INPUT" in result.diagnostics.warnings


def test_proposal_simulation_run_id_is_deterministic_for_request_hash():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_5c",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("EQ_1", status="APPROVED")]
    options = EngineOptions(enable_proposal_simulation=True)
    proposed_trades = [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}]
    request_hash = "sha256:deterministic-hash"

    first = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=proposed_trades,
        request_hash=request_hash,
    )
    second = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=proposed_trades,
        request_hash=request_hash,
    )

    assert first.proposal_run_id == second.proposal_run_id
