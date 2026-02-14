"""
FILE: tests/test_engine.py
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


@pytest.fixture
def base_portfolio():
    return PortfolioSnapshot(
        portfolio_id="pf_test",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.00"))],
    )


@pytest.fixture
def base_options():
    return EngineOptions(
        allow_restricted=False,
        suppress_dust_trades=True,
        block_on_missing_prices=True,
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


def test_banned_assets_excluded(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_BANNED", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_BANNED", status="BANNED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_BANNED", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    # Asset excluded -> 100% Cash -> >5% Limit -> PENDING_REVIEW
    assert result.status == "PENDING_REVIEW"
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_BANNED"


def test_restricted_assets_excluded(base_portfolio, base_options):
    """Hits the 'RESTRICTED' branch in _build_universe."""
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_RESTRICTED", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_RESTRICTED", status="RESTRICTED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_RESTRICTED", price=Decimal("10.0"), currency="SGD")]
    )
    # options.allow_restricted is False by default
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)

    assert result.status == "PENDING_REVIEW"  # 100% Cash
    assert len(result.universe.excluded) == 1
    assert result.universe.excluded[0].reason_code == "SHELF_STATUS_RESTRICTED"


def test_valuation_missing_data_branches(base_options):
    """
    Specifically targets lines in _calculate_valuation where:
    1. Cash FX is missing
    2. Position MarketValue FX is missing
    3. Position Price is missing
    4. Position Price FX is missing
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_val_test",
        base_currency="SGD",
        positions=[
            # Case 2: Market Value provided, but FX missing (EUR->SGD)
            Position(
                instrument_id="EQ_MV_NO_FX",
                quantity=Decimal("10"),
                market_value=Money(amount=Decimal("100.0"), currency="EUR"),
            ),
            # Case 3: No Market Value, No Price found
            Position(instrument_id="EQ_NO_PRICE", quantity=Decimal("10")),
            # Case 4: Price found, but FX missing (JPY->SGD)
            Position(instrument_id="EQ_PRICE_NO_FX", quantity=Decimal("10")),
        ],
        cash_balances=[
            # Case 1: Cash FX missing (GBP->SGD)
            CashBalance(currency="GBP", amount=Decimal("100.0")),
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
        ],
    )

    market_data = MarketDataSnapshot(
        prices=[
            # Added Price for EQ_MV_NO_FX to allow logic to proceed to FX check
            Price(instrument_id="EQ_MV_NO_FX", price=Decimal("10.0"), currency="EUR"),
            Price(instrument_id="EQ_PRICE_NO_FX", price=Decimal("100.0"), currency="JPY"),
        ],
        fx_rates=[],  # No FX rates provided
    )

    model = ModelPortfolio(targets=[])
    shelf = []

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    dq = result.diagnostics.data_quality

    # Assert all branches were hit
    assert any("GBP/SGD" in s for s in dq["fx_missing"])  # Case 1
    assert any("EUR/SGD" in s for s in dq["fx_missing"])  # Case 2
    assert "EQ_NO_PRICE" in dq["price_missing"]  # Case 3
    assert any("JPY/SGD" in s for s in dq["fx_missing"])  # Case 4


def test_valuation_mismatch_warning(base_options):
    """
    RFC-0004 4.3.3: If snapshot MV exists but differs from computed MV > 0.5%, warn.
    """
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

    # It shouldn't block, but should have a warning
    assert result.status == "READY"
    assert len(result.diagnostics.warnings) == 1
    assert "POSITION_VALUE_MISMATCH" in result.diagnostics.warnings[0]
    # Check that allocation was populated
    assert result.before.allocation_by_asset_class[0].key == "EQUITY"
    assert result.before.allocation_by_asset_class[0].value.amount == Decimal("2000.0")


def test_dust_trade_suppression(base_portfolio, base_options):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [
        ShelfEntry(
            instrument_id="EQ_1",
            status="APPROVED",
            min_notional=Money(amount=Decimal("50000.0"), currency="SGD"),
        )
    ]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert len(result.intents) == 0
    assert result.status == "PENDING_REVIEW"
    assert len(result.diagnostics.suppressed_intents) == 1


def test_infeasible_constraint_no_recipients(base_portfolio):
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD")]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.5"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    assert result.status == "BLOCKED"


def test_infeasible_constraint_secondary_breach(base_portfolio):
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_1", weight=Decimal("0.6")),
            ModelTarget(instrument_id="EQ_2", weight=Decimal("0.4")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_2", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_2", price=Decimal("100.0"), currency="SGD"),
        ]
    )
    opts = EngineOptions(single_position_max_weight=Decimal("0.45"))

    result = run_simulation(base_portfolio, market_data, model, shelf, opts)
    assert result.status == "BLOCKED"


def test_sell_intent_generation(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_sell",
        base_currency="SGD",
        positions=[
            Position(
                instrument_id="EQ_1",
                quantity=Decimal("100"),
                market_value=Money(amount=Decimal("10000.0"), currency="SGD"),
            )
        ],
        cash_balances=[],
    )
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_1", weight=Decimal("0.5")),
            ModelTarget(instrument_id="EQ_2", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_1", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_2", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_1", price=Decimal("100.0"), currency="SGD"),
            Price(instrument_id="EQ_2", price=Decimal("100.0"), currency="SGD"),
        ]
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    assert result.intents[0].side == "SELL"
    assert result.intents[0].instrument_id == "EQ_1"
    assert result.intents[1].side == "BUY"
    assert result.intents[1].instrument_id == "EQ_2"


def test_existing_foreign_cash_used_for_fx_deficit(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_foreign_cash",
        base_currency="SGD",
        positions=[],
        cash_balances=[
            CashBalance(currency="SGD", amount=Decimal("1000.0")),
            CashBalance(currency="USD", amount=Decimal("50.0")),
        ],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="US_EQ", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="US_EQ", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="US_EQ", price=Decimal("1.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.0"))],
    )
    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    fx_intents = [i for i in result.intents if i.intent_type == "FX_SPOT"]
    assert float(fx_intents[0].buy_amount) == 479.75


def test_missing_shelf_non_blocking(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_NO_SHELF", weight=Decimal("1.0"))]
    )
    shelf = []
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_NO_SHELF", price=Decimal("10.0"), currency="SGD")]
    )
    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"


def test_sell_only_allows_liquidation(base_options):
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_liq",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_SELL_ONLY", quantity=Decimal("100"))],
    )
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EQ_APPROVED", weight=Decimal("1.0")),
            ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("0.5")),
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="EQ_APPROVED", status="APPROVED"),
        ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EQ_APPROVED", price=Decimal("10.0"), currency="SGD"),
            Price(instrument_id="EQ_SELL_ONLY", price=Decimal("100.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    assert len(result.intents) == 2
    assert result.intents[0].side == "SELL"
    assert result.intents[0].instrument_id == "EQ_SELL_ONLY"
    assert result.intents[1].side == "BUY"
    assert result.intents[1].instrument_id == "EQ_APPROVED"


def test_all_assets_sell_only_blocks_run(base_portfolio, base_options):
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="EQ_SELL_ONLY", weight=Decimal("1.0"))]
    )
    shelf = [ShelfEntry(instrument_id="EQ_SELL_ONLY", status="SELL_ONLY")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_SELL_ONLY", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(base_portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
