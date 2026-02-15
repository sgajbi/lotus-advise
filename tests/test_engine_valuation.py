"""
FILE: tests/test_engine_valuation.py
Tests for Valuation, Data Quality, and Market Data normalization.
"""

from decimal import Decimal

import pytest

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)
from src.core.valuation import build_simulated_state


@pytest.fixture
def base_options():
    return EngineOptions(
        cash_band_min_weight=Decimal("0.00"),
        cash_band_max_weight=Decimal("1.00"),
        single_position_max_weight=None,
    )


def test_valuation_basic_sgd(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_1",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_1", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("5000.00"))],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("50.0"), currency="SGD")]
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Total = 100*50 + 5000 = 10000
    assert result.before.total_value.amount == Decimal("10000.00")
    assert result.before.positions[0].weight == Decimal("0.5")


def test_valuation_missing_price_blocked(base_options):
    """Test RFC-0006B Data Quality Hard Block."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_err",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_NO_PRICE", quantity=Decimal("10"))],
    )
    market_data = MarketDataSnapshot(prices=[])  # Empty
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_NO_PRICE", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "MISSING_DATA" in [r.reason_code for r in result.rule_results]
    assert len(result.diagnostics.data_quality["price_missing"]) > 0


def test_valuation_fx_conversion(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_fx",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_USD", quantity=Decimal("10"))],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_USD", price=Decimal("100.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.5"))],
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_USD", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 10 * 100 USD = 1000 USD * 1.5 = 1500 SGD
    assert result.before.total_value.amount == Decimal("1500.0")
    assert result.before.total_value.currency == "SGD"


def test_valuation_market_value_override_warns(base_options):
    """Test that explicit market_value mismatch triggers warning, but Engine uses Calc Value."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_mv",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_1",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("2000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")]
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Updated: Expect calculated value (100.0) not snapshot (2000.0)
    assert result.before.total_value.amount == Decimal("100.0")
    # Expect warning about the mismatch
    assert any("POSITION_VALUE_MISMATCH" in w for w in result.diagnostics.warnings)


def test_valuation_market_value_non_base(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_non_base_mv",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_USD_MV",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("100.0"), currency="USD"),
            )
        ],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_USD_MV", price=Decimal("10.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_USD_MV", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # 100 USD * 1.35 = 135 SGD. (Not 10*10*1.35=135)
    assert result.before.total_value.amount == Decimal("135.0")
    assert result.status == "READY"


def test_missing_price_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(prices=[])

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert "EQ_1" in result.diagnostics.data_quality["price_missing"]


def test_missing_shelf_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert "EQ_NO_SHELF" in result.diagnostics.data_quality["shelf_missing"]


def test_missing_fx_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("100.0"), currency="USD")],
        fx_rates=[],  # Missing USD/SGD
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert any("USD/SGD" in s for s in result.diagnostics.data_quality["fx_missing"])


def test_valuation_missing_data_branches(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_val_test",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_MV_NO_FX",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("100.0"), currency="EUR"),
            ),
            Position(instrument_id="EQ_NO_PRICE", quantity=Decimal("10")),
            Position(instrument_id="EQ_PRICE_NO_FX", quantity=Decimal("10")),
        ],
        cash_balances=[
            CashBalance(currency="GBP", amount=Decimal("100.0")),
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
        ],
    )

    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_MV_NO_FX", price=Decimal("10.0"), currency="EUR"),
            Price(instrument_id="EQ_PRICE_NO_FX", price=Decimal("100.0"), currency="JPY"),
        ],
        fx_rates=[],
    )

    model = ModelPortfolio(targets=[])
    shelf = []

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    dq = result.diagnostics.data_quality
    assert any("GBP/SGD" in s for s in dq["fx_missing"])
    assert any("EUR/SGD" in s for s in dq["fx_missing"])
    assert "EQ_NO_PRICE" in dq["price_missing"]
    assert any("JPY/SGD" in s for s in dq["fx_missing"])


def test_valuation_mismatch_warning(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_mismatch",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_MISMATCH",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("2000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_MISMATCH", price=Decimal("100.0"), currency="SGD")]
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_MISMATCH", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert len(result.diagnostics.warnings) >= 1
    assert "POSITION_VALUE_MISMATCH" in result.diagnostics.warnings[0]


def test_build_simulated_state_negative_qty():
    """Verifies that negative quantities are correctly valued and not filtered."""
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_neg_test",
        base_currency="SGD",
        positions=[
            Position(instrument_id="SHORT_EQ", quantity=Decimal("-10")),
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("2000.0"))],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="SHORT_EQ", price=Decimal("100.0"), currency="SGD")],
        fx_rates=[],
    )
    shelf = [ShelfEntry(instrument_id="SHORT_EQ", status="APPROVED", asset_class="EQUITY")]

    dq = {}
    warns = []

    state = build_simulated_state(portfolio, market_data, shelf, dq, warns)

    # -10 * 100 = -1000 val. Total = 2000 - 1000 = 1000.
    assert state.total_value.amount == Decimal("1000.0")
    assert len(state.positions) == 1
    assert state.positions[0].quantity == Decimal("-10")
    assert state.positions[0].value_in_base_ccy.amount == Decimal("-1000.0")
    assert state.positions[0].asset_class == "EQUITY"
