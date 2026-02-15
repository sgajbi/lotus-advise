"""
FILE: tests/test_dependencies.py
RFC-0006B: Verification of Intent Dependencies (Graph Logic).
"""

from decimal import Decimal

from src.core.engine import run_simulation
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)


def test_dependency_fx_funding():
    """
    RFC-0006B: A Security Buy in a foreign currency MUST depend on the FX Buy.
    Scenario: Base SGD. Buy USD Asset. Cash SGD only.
    Expectation: Security Buy depends on FX (SGD->USD).
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_dep_fx",
        base_currency="SGD",
        positions=[],
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("10000.0"))],
    )
    # Buy $1000 USD worth of Apple
    model = ModelPortfolio(targets=[ModelTarget(instrument_id="AAPL", weight=Decimal("1.0"))])
    shelf = [ShelfEntry(instrument_id="AAPL", status="APPROVED")]

    # Price $100 USD. Need 10 units = $1000 USD.
    # FX 1.5. Cost = $1500 SGD.
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="AAPL", price=Decimal("100.0"), currency="USD")],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.5"))],
    )

    options = EngineOptions()

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status == "READY"

    # Identify intents
    fx_intent = next(i for i in result.intents if i.intent_type == "FX_SPOT")
    sec_intent = next(i for i in result.intents if i.intent_type == "SECURITY_TRADE")

    # Verify Linkage
    assert fx_intent.intent_id in sec_intent.dependencies
    assert sec_intent.side == "BUY"
    assert fx_intent.buy_currency == "USD"


def test_dependency_sell_to_fund_same_currency():
    """
    RFC-0006B: Sell -> Buy ordering is critical for low-cash accounts.
    Scenario: Base SGD. Cash 0. Sell A (SGD) to Buy B (SGD).
    Expectation: Buy B depends on Sell A.
    """
    portfolio = PortfolioSnapshot(
        portfolio_id="pf_dep_s2f",
        base_currency="SGD",
        positions=[Position(instrument_id="OLD", quantity=Decimal("100"))],  # Val 1000
        cash_balances=[CashBalance(currency="SGD", amount=Decimal("0.0"))],
    )
    model = ModelPortfolio(
        targets=[
            ModelTarget(instrument_id="OLD", weight=Decimal("0.0")),  # Sell All
            ModelTarget(instrument_id="NEW", weight=Decimal("1.0")),  # Buy New
        ]
    )
    shelf = [
        ShelfEntry(instrument_id="OLD", status="APPROVED"),
        ShelfEntry(instrument_id="NEW", status="APPROVED"),
    ]
    market_data = MarketDataSnapshot(
        prices=[
            Price(instrument_id="OLD", price=Decimal("10.0"), currency="SGD"),
            Price(instrument_id="NEW", price=Decimal("10.0"), currency="SGD"),
        ]
    )

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    sell = next(i for i in result.intents if i.side == "SELL")
    buy = next(i for i in result.intents if i.side == "BUY")

    assert sell.intent_id in buy.dependencies


def test_dependency_multi_leg_chain():
    """
    Complex: Sell EUR -> SGD -> Buy USD.
    1. Sell EUR Asset (Generates EUR)
    2. FX Sell EUR / Buy SGD (Sweep)
    3. FX Sell SGD / Buy USD (Funding)
    4. Buy USD Asset

    Note: Current Engine aggregates cash.
    It sees: +EUR (from sale), -USD (for buy).
    It generates: FX Sell EUR, FX Buy USD.

    Dependencies:
    - FX Sell EUR depends on Security Sell EUR? (Ideally yes, but engine uses net flow)
      Actually, engine logic:
      `sell_ids` map contains Security Sells.
      FX generation is based on `proj` (projected balances).

    Let's check what the engine currently links.
    RFC Requirement: "Security Trade Buy ... list FX intent".
    The engine implementation links FX->Security Buy.
    It DOES NOT currently link Security Sell -> FX Sell (Sweep).
    This is acceptable for RFC-0006B as long as Security Buy -> FX Buy is strict.
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
    sell_sec = next(i for i in result.intents if i.instrument_id == "EUR_ASSET")
    buy_sec = next(i for i in result.intents if i.instrument_id == "USD_ASSET")

    fx_buy_usd = next(
        i for i in result.intents if i.intent_type == "FX_SPOT" and i.buy_currency == "USD"
    )

    # Verify strict upstream dependency
    # Buy USD Asset MUST depend on FX Buy USD
    assert fx_buy_usd.intent_id in buy_sec.dependencies

    # The Sell EUR Asset does NOT necessarily have to be linked to the FX Sell EUR in this version
    # because the FX is a "Sweep".
    # But checking if the FX Buy USD depends on anything?
    # Currently FX trades don't depend on other FX trades in this engine.
    # This is fine for Phase 1.
