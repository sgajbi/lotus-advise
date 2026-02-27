from decimal import Decimal

from src.core.common.simulation_shared import (
    apply_fx_spot_to_portfolio,
    apply_security_trade_to_portfolio,
)
from src.core.models import FxSpotIntent, Money, SecurityTradeIntent
from tests.shared.factories import cash, portfolio_snapshot, position


def test_apply_security_trade_updates_position_and_cash_for_buy_and_sell():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_apply_trade",
        base_currency="USD",
        positions=[position("EQ_1", "10")],
        cash_balances=[cash("USD", "1000")],
    )

    apply_security_trade_to_portfolio(
        portfolio,
        SecurityTradeIntent(
            intent_id="oi_buy_1",
            instrument_id="EQ_1",
            side="BUY",
            quantity=Decimal("2"),
            notional=Money(amount=Decimal("200"), currency="USD"),
        ),
    )
    apply_security_trade_to_portfolio(
        portfolio,
        SecurityTradeIntent(
            intent_id="oi_sell_1",
            instrument_id="EQ_1",
            side="SELL",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
        ),
    )

    eq_position = next(p for p in portfolio.positions if p.instrument_id == "EQ_1")
    usd_cash = next(c for c in portfolio.cash_balances if c.currency == "USD")
    assert eq_position.quantity == Decimal("11")
    assert usd_cash.amount == Decimal("900")


def test_apply_security_trade_ignores_incomplete_intent():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_incomplete_trade",
        base_currency="USD",
        positions=[position("EQ_1", "10")],
        cash_balances=[cash("USD", "1000")],
    )

    apply_security_trade_to_portfolio(
        portfolio,
        SecurityTradeIntent(
            intent_id="oi_incomplete",
            instrument_id="EQ_1",
            side="BUY",
            quantity=Decimal("2"),
            notional=None,
        ),
    )

    eq_position = next(p for p in portfolio.positions if p.instrument_id == "EQ_1")
    usd_cash = next(c for c in portfolio.cash_balances if c.currency == "USD")
    assert eq_position.quantity == Decimal("10")
    assert usd_cash.amount == Decimal("1000")


def test_apply_fx_spot_ignores_non_fx_intent_and_updates_only_for_fx_spot():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_fx_apply",
        base_currency="USD",
        positions=[],
        cash_balances=[cash("USD", "1000"), cash("SGD", "0")],
    )
    baseline = [balance.model_copy(deep=True) for balance in portfolio.cash_balances]

    apply_fx_spot_to_portfolio(
        portfolio,
        SecurityTradeIntent(
            intent_id="oi_non_fx",
            instrument_id="EQ_1",
            side="BUY",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
        ),
    )
    assert portfolio.cash_balances == baseline

    apply_fx_spot_to_portfolio(
        portfolio,
        FxSpotIntent(
            intent_id="oi_fx_1",
            pair="SGD/USD",
            buy_currency="SGD",
            buy_amount=Decimal("135"),
            sell_currency="USD",
            sell_amount_estimated=Decimal("100"),
        ),
    )
    usd_cash = next(c for c in portfolio.cash_balances if c.currency == "USD")
    sgd_cash = next(c for c in portfolio.cash_balances if c.currency == "SGD")
    assert usd_cash.amount == Decimal("900")
    assert sgd_cash.amount == Decimal("135")
