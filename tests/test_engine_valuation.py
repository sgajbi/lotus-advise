"""
FILE: tests/test_engine_valuation.py
Tests for Valuation, Data Quality, and Market Data normalization.
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    Position,
    Price,
    ShelfEntry,
)


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
    portfolio = base_options  # Dummy var for fixture
    # Re-using the logic from the big file, creating specific portfolio here
    from src.core.models import CashBalance, PortfolioSnapshot

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
    """
    RFC-0004 4.3.3: If snapshot MV exists but differs from computed MV > 0.5%, warn.
    RFC-0005 Update: If this mismatch causes 'phantom weight' that leads to overselling
    physical units, the engine MUST Block.
    """
    from src.core.models import PortfolioSnapshot

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
    # Computed: 10 * 100 = 1000. Snapshot: 2000. Diff 100%.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_MISMATCH", price=Decimal("100.0"), currency="SGD")]
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_MISMATCH", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Explanation:
    # Engine trusts Snapshot(2000). Target(0). Intent to Sell 2000 SGD value.
    # At Price(100), Sell Qty = 20.
    # Holding = 10.
    # Result = -10.
    # Outcome: BLOCKED (Negative Holding Guard).
    assert result.status == "BLOCKED"

    # Verify the warning is still present (Audit trail)
    assert len(result.diagnostics.warnings) >= 1
    assert "POSITION_VALUE_MISMATCH" in result.diagnostics.warnings[0]


def test_valuation_market_value_non_base(base_options):
    from src.core.models import PortfolioSnapshot

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
    # Price: 10 USD. Qty 10. Computed = 100 USD. FX = 1.35. Total = 135 SGD.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_USD_MV", price=Decimal("10.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    model = ModelPortfolio(targets=[])
    shelf = [ShelfEntry(instrument_id="EQ_USD_MV", status="APPROVED", asset_class="EQUITY")]

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    # Implicit sell to zero
    assert result.status == "PENDING_REVIEW"
    assert result.before.total_value.amount == Decimal("135.0")
    assert result.before.positions[0].value_in_base_ccy.amount == Decimal("135.0")
