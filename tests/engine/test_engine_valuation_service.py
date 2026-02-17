from decimal import Decimal

import pytest

from src.core.models import (
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    Money,
    Position,
    Price,
    ValuationMode,
)
from src.core.valuation import ValuationService, build_simulated_state, get_fx_rate


@pytest.fixture
def market_data():
    return MarketDataSnapshot(
        prices=[
            Price(instrument_id="AAPL", price=Decimal("150.00"), currency="USD"),
            Price(instrument_id="DBS", price=Decimal("30.00"), currency="SGD"),
        ],
        fx_rates=[FxRate(pair="USD/SGD", rate=Decimal("1.35"))],
    )


def test_get_fx_rate_permutations(market_data):
    assert get_fx_rate(market_data, "USD", "SGD") == Decimal("1.35")
    assert round(get_fx_rate(market_data, "SGD", "USD"), 4) == round(
        Decimal("1") / Decimal("1.35"), 4
    )
    assert get_fx_rate(market_data, "USD", "USD") == Decimal("1.0")
    assert get_fx_rate(market_data, "JPY", "USD") is None


def test_valuation_calculated_mode(market_data):
    pos = Position(instrument_id="AAPL", quantity=Decimal("10"))
    options = EngineOptions(valuation_mode=ValuationMode.CALCULATED)
    dq = {}

    summary = ValuationService.value_position(pos, market_data, "SGD", options, dq)

    assert summary.value_in_instrument_ccy.amount == Decimal("1500.00")
    assert summary.value_in_base_ccy.amount == Decimal("2025.00")


def test_valuation_trust_snapshot_mode(market_data):
    pos = Position(
        instrument_id="AAPL",
        quantity=Decimal("10"),
        market_value=Money(amount=Decimal("2000.00"), currency="USD"),
    )
    options = EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT)
    dq = {}

    summary = ValuationService.value_position(pos, market_data, "SGD", options, dq)

    assert summary.value_in_instrument_ccy.amount == Decimal("2000.00")
    assert summary.value_in_base_ccy.amount == Decimal("2700.00")


def test_valuation_zero_price_handling(market_data):
    market_data.prices.append(
        Price(instrument_id="WORTHLESS", price=Decimal("0.0"), currency="USD")
    )
    pos = Position(instrument_id="WORTHLESS", quantity=Decimal("1000"))

    dq = {}
    summary = ValuationService.value_position(
        pos,
        market_data,
        "USD",
        EngineOptions(valuation_mode=ValuationMode.CALCULATED),
        dq,
    )

    assert summary.value_in_base_ccy.amount == Decimal("0")


def test_valuation_missing_fx_logging(market_data):
    market_data.prices.append(
        Price(instrument_id="NINTENDO", price=Decimal("5000"), currency="JPY")
    )
    pos = Position(instrument_id="NINTENDO", quantity=Decimal("100"))

    dq = {}
    summary = ValuationService.value_position(
        pos,
        market_data,
        "USD",
        EngineOptions(valuation_mode=ValuationMode.CALCULATED),
        dq,
    )

    assert summary.value_in_base_ccy.amount == Decimal("0")

    from src.core.models import PortfolioSnapshot

    pf = PortfolioSnapshot(portfolio_id="p1", base_currency="USD", positions=[pos])
    warns = []

    _ = build_simulated_state(pf, market_data, [], dq, warns)

    assert "JPY/USD" in dq["fx_missing"]
