"""
FILE: tests/test_dependencies.py
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    FxSpotIntent,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    Price,
    SecurityTradeIntent,
    ShelfEntry,
)


def test_dependency_chain_generation():
    """
    Scenario: Buy DBS (SGD) using USD Base.
    Expect: FX Buy SGD (dependent on nothing) -> Buy DBS (dependent on FX).
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_dep_1",
        base_currency="USD",
        positions=[],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("100000"))],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="DBS", price=Decimal("30.00"), currency="SGD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="DBS", weight=Decimal("0.5"))])
    shelf = [ShelfEntry(instrument_id="DBS", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    # Find intents
    # Fix: Filter strictly by type
    fx_intents = [i for i in result.intents if isinstance(i, FxSpotIntent)]
    sec_intents = [i for i in result.intents if isinstance(i, SecurityTradeIntent)]

    assert len(fx_intents) == 1
    assert len(sec_intents) == 1

    fx = fx_intents[0]
    sec = sec_intents[0]

    assert fx.buy_currency == "SGD"
    assert sec.instrument_id == "DBS"

    # Check dependency
    assert fx.intent_id in sec.dependencies


def test_dependency_multi_leg_chain():
    """
    Complex: Sell EUR -> SGD -> Buy USD.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_chain",
        base_currency="SGD",
        positions=[
            Position(instrument_id="EUR_ASSET", quantity=Decimal("10")),  # 10*100 = 1000 EUR
        ],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("0.0"))],
    )

    # Swap EUR Asset for USD Asset
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="EUR_ASSET", weight=Decimal("0.0")),
            ModelTarget(instrument_id="USD_ASSET", weight=Decimal("1.0")),
        ]
    )

    shelf = [
        ShelfEntry(instrument_id="EUR_ASSET", status="APPROVED"),
        ShelfEntry(instrument_id="USD_ASSET", status="APPROVED"),
    ]

    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="EUR_ASSET", price=Decimal("100.0"), currency="EUR"),
            Price(instrument_id="USD_ASSET", price=Decimal("100.0"), currency="USD"),
        ],
        fx_rates=[
            FxRate(pair="EUR/SGD", rate=Decimal("1.5")),  # 1000 EUR -> 1500 SGD
            FxRate(pair="USD/SGD", rate=Decimal("1.3")),  # Need ~1153 USD
        ],
    )

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    # Intents: Sell EUR_ASSET, Buy USD_ASSET, FX Sell EUR, FX Buy USD

    # Fix: Filter by type before accessing instrument_id
    sec_intents = [i for i in result.intents if isinstance(i, SecurityTradeIntent)]
    fx_intents = [i for i in result.intents if isinstance(i, FxSpotIntent)]

    buy_sec = next(i for i in sec_intents if i.instrument_id == "USD_ASSET")
    # sell_sec unused

    # Check FX linking
    # Buy USD_ASSET (USD) -> needs USD.
    # FX Buy USD (from SGD) must exist.
    fx_buy_usd = next(i for i in fx_intents if i.buy_currency == "USD")

    assert fx_buy_usd.intent_id in buy_sec.dependencies
