"""
FILE: tests/test_engine_safety.py
Tests for RFC-0005 Safety Guardrails (Negative Holdings, Reconciliation).
"""

from decimal import Decimal

import pytest

from src.core.engine import _generate_fx_and_simulate, run_simulation
from src.core.models import (
    CashBalance,
    FxRate,
    IntentRationale,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    OrderIntent,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)


def test_negative_holding_guard(base_options):
    """
    Slice 2: Verifies that if simulation results in negative holdings (overselling),
    the status is forced to BLOCKED.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_neg",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_1", quantity=Decimal("10"))],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    # Intent to sell 20 units (Holding is 10)
    intents = [
        OrderIntent(
            intent_id="oi_oversell",
            side="SELL",
            instrument_id="EQ_1",
            quantity=Decimal("20"),
            notional=Money(amount=Decimal("2000"), currency="SGD"),
            rationale=IntentRationale(code="TEST", message="Oversell"),
        )
    ]

    intents, after, rules, status = _generate_fx_and_simulate(
        portfolio, market_data, [], intents, base_options, Decimal("1000")
    )

    assert status == "BLOCKED"


def test_reconciliation_mismatch_guard(base_options):
    """
    Slice 2: Verifies that if After Value differs from Before Value > Tolerance,
    the status is forced to BLOCKED.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_recon",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    # Intent: "Burn" money (Sell 1000 SGD, Buy 0 USD)
    intents = [
        OrderIntent(
            intent_id="oi_bad_fx",
            intent_type="FX_SPOT",
            side="SELL_BASE_BUY_QUOTE",
            pair="USD/SGD",
            buy_currency="USD",
            buy_amount=Decimal("0.0"),
            sell_currency="SGD",
            estimated_sell_amount=Decimal("500.0"),
            rationale=IntentRationale(code="TEST", message="Burn Money"),
        )
    ]

    # Before Value = 1000. After Value = 500 + 0 = 500. Diff = 500.
    intents, after, rules, status = _generate_fx_and_simulate(
        portfolio, market_data, [], intents, base_options, Decimal("1000.0")
    )

    assert status == "BLOCKED"


def test_simulation_crash_on_missing_fx(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_crash", base_currency="SGD", positions=[], cash_balances=[]
    )
    # Missing FX rate for USD/SGD
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])

    intents = [
        OrderIntent(
            intent_id="oi_1",
            side="SELL",
            instrument_id="DUMMY_CRASH",
            quantity=Decimal("10"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            rationale=IntentRationale(code="TEST", message="Test"),
        )
    ]

    with pytest.raises(ValueError, match="Missing FX rate for USD/SGD"):
        _generate_fx_and_simulate(
            portfolio, market_data, [], intents, base_options, Decimal("1000")
        )


def test_simulation_creates_new_cash_currency(base_options):
    """
    Coverage fix for lazy cash creation.
    Scenario: Portfolio has SGD. We buy a USD asset.
    Result: Engine creates 'USD' entry in cash_balances.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_lazy_cash",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_STOCK", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="US_STOCK", status="APPROVED")]

    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_STOCK", price=Decimal("100.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.5"))],
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "READY"
    usd_cash = next((c for c in result.after_simulated.cash_balances if c.currency == "USD"), None)
    assert usd_cash is not None
