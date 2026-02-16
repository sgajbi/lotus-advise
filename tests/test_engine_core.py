"""
FILE: tests/test_engine_core.py
"""

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
    """Standard Setup: 100k USD Cash, AAPL & DBS available."""
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
    """Happy Path: Buy 50% AAPL."""
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.5"))])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "READY"
    assert len(result.intents) == 1
    intent = result.intents[0]
    assert isinstance(intent, SecurityTradeIntent)
    assert intent.side == "BUY"
    assert intent.instrument_id == "AAPL"
    # 50k / 150 = 333.33 -> 333
    assert intent.quantity == Decimal("333")


def test_fx_hub_and_spoke_funding(base_context):
    """Complex Path: Buy Foreign Asset (DBS in SGD). Checks FX generation & linking."""
    pf, mkt, shelf = base_context
    # Target 50% DBS (SGD)
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="DBS", weight=Decimal("0.5"))])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert result.status == "READY"
    # Expect 1 FX Buy (USD->SGD) and 1 Security Buy (DBS)
    assert len(result.intents) == 2

    fx = result.intents[0]
    sec = result.intents[1]

    assert isinstance(fx, FxSpotIntent)
    assert fx.buy_currency == "SGD"
    assert fx.pair == "SGD/USD"

    assert isinstance(sec, SecurityTradeIntent)
    assert sec.instrument_id == "DBS"

    # CRITICAL: Verify Dependency Linking
    assert fx.intent_id in sec.dependencies


def test_universe_banned_asset_exclusion(base_context):
    """Universe Logic: Banned assets should be excluded from targets."""
    pf, mkt, shelf = base_context
    # User asks for BANNED_ASSET
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="BANNED_ASSET", weight=Decimal("0.5"))]
    )

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    # Logic: Banned asset removed from universe -> Weight 0 -> No trade generated (since not held)
    assert len(result.intents) == 0
    # Check it appears in excluded list
    assert any(e.instrument_id == "BANNED_ASSET" for e in result.universe.excluded)


def test_universe_sell_only_logic(base_context):
    """Universe Logic: SELL_ONLY asset held should be sold to 0 if not in model, or limited if in model."""
    pf, mkt, shelf = base_context
    # Portfolio holds SELL_ONLY_ASSET
    pf.positions.append(Position(instrument_id="SELL_ONLY_ASSET", quantity=Decimal("100")))
    mkt.prices.append(Price(instrument_id="SELL_ONLY_ASSET", price=Decimal("10"), currency="USD"))

    # Model asks for 0% (Implied sell)
    model = ModelPortfolio(targets=[])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "SELL_ONLY_ASSET"
    assert result.intents[0].side == "SELL"
    assert result.intents[0].quantity == Decimal("100")


def test_target_normalization_over_100(base_context):
    """Target Logic: Weights summing > 100% should be scaled down."""
    pf, mkt, shelf = base_context
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="AAPL", weight=Decimal("0.8")),
            ModelTarget(instrument_id="DBS", weight=Decimal("0.8")),
        ]
    )

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    # Total 1.6 -> Scaled to 0.5 each
    # AAPL: 100k * 0.5 / 150 = 333
    # DBS: 100k * 0.5 / (30/1.35) = 2250

    assert result.status == "PENDING_REVIEW"  # Scaled implies review

    aapl_intent = next(
        i
        for i in result.intents
        if isinstance(i, SecurityTradeIntent) and i.instrument_id == "AAPL"
    )
    assert aapl_intent.quantity == Decimal("333")


def test_target_single_position_cap(base_context):
    """Constraint: Single Position Max Weight."""
    pf, mkt, shelf = base_context
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.5"))])

    # Cap at 10%
    options = EngineOptions(single_position_max_weight=Decimal("0.10"))

    result = run_simulation(pf, mkt, model, shelf, options)

    # 100k * 10% = 10k. 10k / 150 = 66.6 -> 66 units
    intent = result.intents[0]
    assert intent.quantity == Decimal("66")
    # Status should be PENDING_REVIEW due to cap breach
    assert result.status == "PENDING_REVIEW"


def test_missing_price_blocking(base_context):
    """DQ: Missing price should block by default."""
    pf, mkt, shelf = base_context
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="UNKNOWN_ASSET", weight=Decimal("0.1"))]
    )
    # Add to shelf so it passes universe check
    shelf.append(ShelfEntry(instrument_id="UNKNOWN_ASSET", status="APPROVED", asset_class="EQUITY"))

    # But DO NOT add to market data

    result = run_simulation(pf, mkt, model, shelf, EngineOptions(block_on_missing_prices=True))

    assert result.status == "BLOCKED"
    assert "UNKNOWN_ASSET" in result.diagnostics.data_quality["price_missing"]


def test_dust_suppression(base_context):
    """Intent Logic: Small trades should be suppressed."""
    pf, mkt, shelf = base_context
    # Very small target
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("0.0001"))])

    # Min trade 1000 USD
    options = EngineOptions(
        suppress_dust_trades=True, min_trade_notional=Money(amount=Decimal("1000"), currency="USD")
    )

    result = run_simulation(pf, mkt, model, shelf, options)

    assert len(result.intents) == 0
    assert len(result.diagnostics.suppressed_intents) == 1
    assert result.diagnostics.suppressed_intents[0].instrument_id == "AAPL"
