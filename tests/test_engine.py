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

    # Check for bad position handling
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_bad_pos",
        base_currency="SGD",
        positions=[Position(instrument_id="EQ_BAD", quantity=Decimal("100"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="EQ_1", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="EQ_1", status="APPROVED")]
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EQ_1", price=Decimal("10.0"), currency="SGD")]
    )

    result = run_simulation(portfolio, market_data, model, shelf, base_options)
    assert result.status == "BLOCKED"
    assert "EQ_BAD" in result.diagnostics.data_quality["price_missing"]


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
