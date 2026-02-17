from decimal import Decimal

import pytest

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    FxSpotIntent,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
    SecurityTradeIntent,
    ShelfEntry,
)


@pytest.fixture
def base_context():
    pf = PortfolioSnapshot(
        portfolio_id="pf_1",
        base_currency="USD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("100000"))],
    )
    mkt = MarketDataSnapshot(
        prices=[
            Price(instrument_id="AAPL", price=Decimal("150.00"), currency="USD"),
            Price(instrument_id="DBS", price=Decimal("30.00"), currency="SGD"),
            Price(instrument_id="BANNED_ASSET", price=Decimal("10.00"), currency="USD"),
        ],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    shelf = [
        ShelfEntry(instrument_id="AAPL", status="APPROVED", asset_class="EQUITY"),
        ShelfEntry(instrument_id="DBS", status="APPROVED", asset_class="EQUITY"),
        ShelfEntry(instrument_id="BANNED_ASSET", status="BANNED", asset_class="EQUITY"),
        ShelfEntry(instrument_id="RESTRICTED_ASSET", status="RESTRICTED", asset_class="EQUITY"),
        ShelfEntry(instrument_id="SELL_ONLY_ASSET", status="SELL_ONLY", asset_class="EQUITY"),
    ]
    return pf, mkt, shelf


def test_standard_buy_security(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.5"))])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "READY"
    assert len(result.intents) == 1
    intent = result.intents[0]
    assert isinstance(intent, SecurityTradeIntent)
    assert intent.side == "BUY"
    assert intent.instrument_id == "AAPL"
    assert intent.quantity == Decimal("333")


def test_fx_hub_and_spoke_funding(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="DBS", weight=Decimal("0.5"))])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "READY"
    assert len(result.intents) == 2

    fx = result.intents[0]
    sec = result.intents[1]

    assert isinstance(fx, FxSpotIntent)
    assert fx.buy_currency == "SGD"
    assert fx.pair == "SGD/USD"

    assert isinstance(sec, SecurityTradeIntent)
    assert sec.instrument_id == "DBS"
    assert fx.intent_id in sec.dependencies


def test_universe_banned_asset_exclusion(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="BANNED_ASSET", weight=Decimal("0.5"))]
    )

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert len(result.intents) == 0
    assert any(e.instrument_id == "BANNED_ASSET" for e in result.universe.excluded)


def test_universe_sell_only_logic(base_context):
    pf, mkt, shelf = base_context
    pf.positions.append(Position(instrument_id="SELL_ONLY_ASSET", quantity=Decimal("100")))
    mkt.prices.append(Price(instrument_id="SELL_ONLY_ASSET", price=Decimal("10"), currency="USD"))
    model = ModelPortfolio(targets=[])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "SELL_ONLY_ASSET"
    assert result.intents[0].side == "SELL"
    assert result.intents[0].quantity == Decimal("100")


def test_target_normalization_over_100(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="AAPL", weight=Decimal("0.8")),
            ModelTarget(instrument_id="DBS", weight=Decimal("0.8")),
        ]
    )
    options = EngineOptions(fx_buffer_pct=Decimal("0.0"))

    result = run_simulation(pf, mkt, model, shelf, options)

    assert result.status == "PENDING_REVIEW"

    aapl_intent = next(
        i
        for i in result.intents
        if isinstance(i, SecurityTradeIntent) and i.instrument_id == "AAPL"
    )
    assert aapl_intent.quantity == Decimal("333")


def test_target_single_position_cap(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.5"))])
    options = EngineOptions(single_position_max_weight=Decimal("0.10"))

    result = run_simulation(pf, mkt, model, shelf, options)

    intent = result.intents[0]
    assert intent.quantity == Decimal("66")
    assert result.status == "PENDING_REVIEW"


def test_missing_price_blocking(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="UNKNOWN_ASSET", weight=Decimal("0.1"))]
    )
    shelf.append(ShelfEntry(instrument_id="UNKNOWN_ASSET", status="APPROVED", asset_class="EQUITY"))

    result = run_simulation(pf, mkt, model, shelf, EngineOptions(block_on_missing_prices=True))

    assert result.status == "BLOCKED"
    assert "UNKNOWN_ASSET" in result.diagnostics.data_quality["price_missing"]


def test_dust_suppression(base_context):
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.0001"))])
    options = EngineOptions(
        suppress_dust_trades=True,
        min_trade_notional=Money(amount=Decimal("1000"), currency="USD"),
    )

    result = run_simulation(pf, mkt, model, shelf, options)

    assert len(result.intents) == 0
    assert len(result.diagnostics.suppressed_intents) == 1
    assert result.diagnostics.suppressed_intents[0].instrument_id == "AAPL"
