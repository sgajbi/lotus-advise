from decimal import Decimal
from unittest.mock import patch

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import EngineOptions, Money, Reconciliation
from tests.factories import (
    cash,
    market_data_snapshot,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
)


def test_proposal_simulation_applies_cash_flows_before_trades():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_1",
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
        proposed_cash_flows=[{"currency": "USD", "amount": "500"}],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "5"}],
        request_hash="proposal_hash",
    )

    assert result.status == "READY"
    assert result.intents[0].intent_type == "CASH_FLOW"
    assert result.intents[1].intent_type == "SECURITY_TRADE"
    usd_cash = next(c for c in result.after_simulated.cash_balances if c.currency == "USD")
    assert usd_cash.amount == Decimal("1000")
    eq_position = next(p for p in result.after_simulated.positions if p.instrument_id == "EQ_1")
    assert eq_position.quantity == Decimal("5")


def test_proposal_simulation_blocks_negative_cash_withdrawal():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_2",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    options = EngineOptions(enable_proposal_simulation=True, proposal_block_negative_cash=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data_snapshot(prices=[], fx_rates=[]),
        shelf=[],
        options=options,
        proposed_cash_flows=[{"currency": "USD", "amount": "-2000"}],
        proposed_trades=[],
        request_hash="proposal_hash",
    )

    assert result.status == "BLOCKED"
    assert "PROPOSAL_WITHDRAWAL_NEGATIVE_CASH" in result.diagnostics.warnings


def test_proposal_simulation_orders_intents_deterministically():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_3",
        base_currency="USD",
        positions=[position("EQ_Z", "5"), position("EQ_A", "5")],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("EQ_A", "10", "USD"),
            price("EQ_B", "10", "USD"),
            price("EQ_C", "10", "USD"),
            price("EQ_Z", "10", "USD"),
        ],
        fx_rates=[],
    )
    shelf = [
        shelf_entry("EQ_A", status="APPROVED"),
        shelf_entry("EQ_B", status="APPROVED"),
        shelf_entry("EQ_C", status="APPROVED"),
        shelf_entry("EQ_Z", status="APPROVED"),
    ]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[{"currency": "USD", "amount": "100"}],
        proposed_trades=[
            {"side": "BUY", "instrument_id": "EQ_C", "quantity": "1"},
            {"side": "SELL", "instrument_id": "EQ_Z", "quantity": "1"},
            {"side": "BUY", "instrument_id": "EQ_B", "quantity": "1"},
            {"side": "SELL", "instrument_id": "EQ_A", "quantity": "1"},
        ],
        request_hash="proposal_hash",
    )

    assert [intent.intent_type for intent in result.intents] == [
        "CASH_FLOW",
        "SECURITY_TRADE",
        "SECURITY_TRADE",
        "SECURITY_TRADE",
        "SECURITY_TRADE",
    ]
    trades = [intent for intent in result.intents if intent.intent_type == "SECURITY_TRADE"]
    assert [trade.side for trade in trades] == ["SELL", "SELL", "BUY", "BUY"]
    assert [trade.instrument_id for trade in trades] == ["EQ_A", "EQ_Z", "EQ_B", "EQ_C"]


def test_proposal_simulation_blocks_shelf_disallowed_buy():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_4",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("EQ_1", status="SELL_ONLY")]
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        request_hash="proposal_hash",
    )

    assert result.status == "BLOCKED"
    assert "PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF" in result.diagnostics.warnings


def test_proposal_simulation_supports_notional_input_path():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_5",
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
                "notional": {"amount": "200", "currency": "USD"},
            }
        ],
        request_hash="proposal_hash_notional",
    )

    trade = next(intent for intent in result.intents if intent.intent_type == "SECURITY_TRADE")
    assert trade.quantity == Decimal("2")
    assert trade.notional.amount == Decimal("200")
    usd_cash = next(c for c in result.after_simulated.cash_balances if c.currency == "USD")
    assert usd_cash.amount == Decimal("800")
    assert result.status == "READY"


def test_proposal_simulation_records_missing_price_data_quality():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_6",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    options = EngineOptions(enable_proposal_simulation=True, block_on_missing_prices=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data_snapshot(prices=[], fx_rates=[]),
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        request_hash="proposal_hash_missing_price",
    )

    assert result.status == "READY"
    assert "EQ_1" in result.diagnostics.data_quality["price_missing"]
    assert result.intents == []
    assert all(
        rule.rule_id != "DATA_QUALITY" or rule.status == "PASS" for rule in result.rule_results
    )


def test_proposal_simulation_records_missing_fx_data_quality():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_7",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "EUR")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True, block_on_missing_fx=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        request_hash="proposal_hash_missing_fx",
    )

    assert result.status == "READY"
    assert "EUR/USD" in result.diagnostics.data_quality["fx_missing"]
    assert result.intents == []
    assert all(
        rule.rule_id != "DATA_QUALITY" or rule.status == "PASS" for rule in result.rule_results
    )


def test_proposal_simulation_records_missing_fx_for_cash_flow_delta():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_7b",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    options = EngineOptions(enable_proposal_simulation=True, block_on_missing_fx=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data_snapshot(prices=[], fx_rates=[]),
        shelf=[],
        options=options,
        proposed_cash_flows=[{"currency": "EUR", "amount": "100"}],
        proposed_trades=[],
        request_hash="proposal_hash_missing_fx_cash_delta",
    )

    assert result.status == "READY"
    assert "EUR/USD" in result.diagnostics.data_quality["fx_missing"]


def test_proposal_simulation_records_missing_shelf_data_quality():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_8",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        request_hash="proposal_hash_missing_shelf",
    )

    assert result.status == "BLOCKED"
    assert "EQ_1" in result.diagnostics.data_quality["shelf_missing"]
    data_quality_rule = next(rule for rule in result.rule_results if rule.rule_id == "DATA_QUALITY")
    assert data_quality_rule.status == "FAIL"


def test_proposal_simulation_blocks_restricted_buy_when_not_allowed():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_9",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True, allow_restricted=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("EQ_1", status="RESTRICTED")],
        options=options,
        proposed_cash_flows=[],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
        request_hash="proposal_hash_restricted",
    )

    assert result.status == "BLOCKED"
    assert "PROPOSAL_TRADE_NOT_SUPPORTED_BY_SHELF" in result.diagnostics.warnings


def test_proposal_simulation_can_apply_cash_flows_after_trades():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_10",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True, proposal_apply_cash_flows_first=False)

    result = run_proposal_simulation(
        portfolio=portfolio,
        market_data=market_data,
        shelf=[shelf_entry("EQ_1", status="APPROVED")],
        options=options,
        proposed_cash_flows=[{"currency": "USD", "amount": "200"}],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"}],
        request_hash="proposal_hash_cash_late",
    )

    assert result.intents[0].intent_type == "SECURITY_TRADE"
    assert result.intents[1].intent_type == "CASH_FLOW"
    usd_cash = next(c for c in result.after_simulated.cash_balances if c.currency == "USD")
    assert usd_cash.amount == Decimal("1000")
    eq_position = next(p for p in result.after_simulated.positions if p.instrument_id == "EQ_1")
    assert eq_position.quantity == Decimal("2")
    assert result.status == "READY"


def test_proposal_simulation_reconciliation_mismatch_blocks_run():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_prop_11",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "100", "USD")], fx_rates=[])
    options = EngineOptions(enable_proposal_simulation=True)

    with patch(
        "src.core.advisory_engine.build_reconciliation",
        return_value=(
            Reconciliation(
                before_total_value=Money(amount=Decimal("1000"), currency="USD"),
                after_total_value=Money(amount=Decimal("900"), currency="USD"),
                delta=Money(amount=Decimal("-100"), currency="USD"),
                tolerance=Money(amount=Decimal("0"), currency="USD"),
                status="MISMATCH",
            ),
            Decimal("1"),
            Decimal("0"),
        ),
    ):
        result = run_proposal_simulation(
            portfolio=portfolio,
            market_data=market_data,
            shelf=[shelf_entry("EQ_1", status="APPROVED")],
            options=options,
            proposed_cash_flows=[],
            proposed_trades=[{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
            request_hash="proposal_hash_recon_mismatch",
        )

    assert result.status == "BLOCKED"
    assert any(rule.rule_id == "RECONCILIATION" for rule in result.rule_results)
