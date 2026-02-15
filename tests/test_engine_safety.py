"""
FILE: tests/test_engine_safety.py
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    FxRate,  # Added
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,  # Added
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)


def get_base_data():
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_safe",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_1", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("1000.0"))],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")], fx_rates=[]
    )
    # Model asks to SELL everything (weight 0)
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("0.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    return portfolio, market_data, model, shelf


def test_safety_no_shorting_block(base_options):
    """
    Simulate a scenario where logic (or data error) tries to sell more than held.
    """
    portfolio, market_data, model, shelf = get_base_data()

    # Poison the input: High Market Value, Low Quantity
    portfolio.positions[0].quantity = Decimal("10")
    # MV implies we have 1000 units (at px 10)
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    # Check for specific Rule Failure
    rule = next((r for r in result.rule_results if r.rule_id == "NO_SHORTING"), None)
    assert rule is not None
    assert rule.status == "FAIL"
    assert rule.reason_code == "SELL_EXCEEDS_HOLDINGS"


def test_safety_insufficient_cash_block(base_options):
    """
    Test that running out of cash blocks the sim.
    Scenario: Buying a new asset with target weight > cash available.
    """
    portfolio, market_data, model, shelf = get_base_data()

    # Start with very little cash
    portfolio.cash_balances[0].amount = Decimal("100.0")

    market_data.prices = [Price(instrument_id="US_EQ", price=Decimal("10.0"), currency="USD")]
    # FX Rate 1.0.
    market_data.fx_rates = [FxRate(pair="USD/SGD", rate=Decimal("1.0"))]
    model.targets = [ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))]
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]

    # Ensure fx buffer is ON
    base_options.fx_buffer_pct = Decimal("0.05")  # 5% buffer

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "INSUFFICIENT_CASH"), None)
    assert rule is not None
    assert rule.status == "FAIL"


def test_reconciliation_object_populated_on_success(base_options):
    """Verify reconciliation object is present and OK for valid runs."""
    portfolio, market_data, model, shelf = get_base_data()
    # Simple valid drift
    model.targets[0].weight = Decimal("0.5")  # Sell half

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # We accept READY or PENDING_REVIEW (soft fails), as long as it's not BLOCKED
    assert result.status in ["READY", "PENDING_REVIEW"]
    assert result.reconciliation is not None
    assert result.reconciliation.status == "OK"
    assert abs(result.reconciliation.delta.amount) < Decimal("1.0")
