"""
FILE: tests/test_engine_coverage.py
Targeted tests to ensure 100% branch coverage in engine.py.
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    EngineOptions,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    Price,
)


def test_coverage_target_missing_shelf_entry():
    """
    Hits engine.py: _build_universe -> if not shelf_ent: dq_log...
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1", base_currency="SGD", positions=[], cash_balances=[]
    )
    # Target "GHOST" exists in Model but not in Shelf
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="GHOST", weight=Decimal("0.1"))])
    shelf = []  # Empty shelf
    market_data = MarketDataSnapshot(prices=[])

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    assert result.status == "BLOCKED"
    assert "GHOST" in result.diagnostics.data_quality["shelf_missing"]


def test_coverage_holding_missing_shelf_with_market_data():
    """
    Hits engine.py: _build_universe -> if not shelf_ent: if curr: excluded.append(...)
    Scenario: We hold a position, but it's removed from the Shelf. We have price data.
    Result: Implicit lock (Excluded).
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_2",
        base_currency="SGD",
        positions=[Position(instrument_id="DELISTED", quantity=Decimal("100"))],
        cash_balances=[],
    )
    # We hold DELISTED.
    # We construct 'curr' via valuation implicitly in engine.

    model = ModelPortfolio(targets=[])
    shelf = []  # Missing shelf entry
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="DELISTED", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    # Should be excluded with specific reason
    excl = next((e for e in result.universe.excluded if e.instrument_id == "DELISTED"), None)
    assert excl is not None
    assert excl.reason_code == "LOCKED_DUE_TO_MISSING_SHELF"

    # Ensure it's not sold
    assert not any(i.instrument_id == "DELISTED" for i in result.intents)


def test_coverage_fx_sweep_missing_rate():
    """
    Hits engine.py: _generate_fx_and_simulate -> if options.block_on_missing_fx -> return BLOCKED
    Scenario: Cash Balance in USD (needs sweep), no Trade Intents, no USD/SGD rate.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sweep",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("100.0"))],
    )
    # No trades, just a pure sweep scenario
    model = ModelPortfolio(targets=[])
    shelf = []
    market_data = MarketDataSnapshot(prices=[], fx_rates=[])  # No FX rates

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    assert result.status == "BLOCKED"
    assert "USD/SGD" in result.diagnostics.data_quality["fx_missing"]
