from decimal import Decimal

from src.core.common.simulation_shared import (
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    ensure_cash_balance,
    ensure_position,
)
from src.core.compliance import RuleEngine
from src.core.models import EngineOptions, SecurityTradeIntent
from src.core.valuation import build_simulated_state
from tests.engine.coverage.helpers import empty_diagnostics
from tests.factories import cash, market_data_snapshot, portfolio_snapshot


def test_ensure_helpers_create_missing_entries():
    portfolio = portfolio_snapshot(portfolio_id="pf_shared_1", base_currency="USD")
    position = ensure_position(portfolio, "EQ_1")
    cash_balance = ensure_cash_balance(portfolio, "USD")

    assert position.instrument_id == "EQ_1"
    assert cash_balance.currency == "USD"
    assert cash_balance.amount == Decimal("0")


def test_apply_security_trade_to_portfolio_mutates_position_and_cash():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_2",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    intent = SecurityTradeIntent(
        intent_id="oi_1",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("2"),
        notional={"amount": Decimal("200"), "currency": "USD"},
        notional_base={"amount": Decimal("200"), "currency": "USD"},
    )

    apply_security_trade_to_portfolio(portfolio, intent)

    assert portfolio.positions[0].instrument_id == "EQ_1"
    assert portfolio.positions[0].quantity == Decimal("2")
    assert portfolio.cash_balances[0].amount == Decimal("800")


def test_derive_status_from_rules_matches_ready_outcome():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_3",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    diagnostics = empty_diagnostics()
    state = build_simulated_state(
        portfolio=portfolio,
        market_data=market_data_snapshot(prices=[], fx_rates=[]),
        shelf=[],
        dq_log=diagnostics.data_quality,
        warnings=diagnostics.warnings,
        options=EngineOptions(),
    )
    rules = RuleEngine.evaluate(state, EngineOptions(), diagnostics)

    assert derive_status_from_rules(rules) == "READY"


def test_build_reconciliation_returns_ok_for_expected_total():
    reconciliation, recon_diff, tolerance = build_reconciliation(
        before_total=Decimal("100"),
        after_total=Decimal("110"),
        expected_after_total=Decimal("110"),
        base_currency="USD",
    )

    assert reconciliation.status == "OK"
    assert recon_diff == Decimal("0")
    assert tolerance > Decimal("0")
