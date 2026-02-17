from decimal import Decimal

import pytest

from src.core.models import (
    CashBalance,
    FxRate,
    MarketDataSnapshot,
    ModelPortfolio,
    ModelTarget,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)


@pytest.fixture
def base_inputs():
    pf = PortfolioSnapshot(
        portfolio_id="gap_fill",
        base_currency="USD",
        positions=[Position(instrument_id="LOCKED_ASSET", quantity=Decimal("100"))],
        cash_balances=[CashBalance(currency="JPY", amount=Decimal("1000"))],
    )
    mkt = MarketDataSnapshot(
        prices=[
            Price(instrument_id="LOCKED_ASSET", price=Decimal("10"), currency="USD"),
            Price(instrument_id="TARGET_ASSET", price=Decimal("10"), currency="USD"),
        ],
        fx_rates=[FxRate(pair="JPY/USD", rate=Decimal("0.01"))],
    )
    shelf = [
        ShelfEntry(instrument_id="LOCKED_ASSET", status="RESTRICTED"),
        ShelfEntry(instrument_id="TARGET_ASSET", status="APPROVED"),
    ]
    model = ModelPortfolio(
        targets=[ModelTarget(instrument_id="TARGET_ASSET", weight=Decimal("0.5"))]
    )
    return pf, mkt, model, shelf
