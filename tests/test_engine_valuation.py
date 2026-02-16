"""
FILE: tests/test_engine_valuation.py
"""

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
        fx_rates=[
            FxRate(pair="USD/SGD", rate=Decimal("1.35")),
        ],
    )


def test_get_fx_rate_permutations(market_data):
    """Test all FX lookup paths."""
    # Direct
    assert get_fx_rate(market_data, "USD", "SGD") == Decimal("1.35")
    # Inverse
    assert round(get_fx_rate(market_data, "SGD", "USD"), 4) == round(
        Decimal("1") / Decimal("1.35"), 4
    )
    # Identity
    assert get_fx_rate(market_data, "USD", "USD") == Decimal("1.0")
    # Missing
    assert get_fx_rate(market_data, "JPY", "USD") is None


def test_valuation_calculated_mode(market_data):
    """Test standard Price * Qty valuation."""
    pos = Position(instrument_id="AAPL", quantity=Decimal("10"))  # 1500 USD
    options = EngineOptions(valuation_mode=ValuationMode.CALCULATED)
    dq = {}

    summary = ValuationService.value_position(pos, market_data, "SGD", options, dq)

    assert summary.value_in_instrument_ccy.amount == Decimal("1500.00")
    # Converted to SGD: 1500 * 1.35 = 2025
    assert summary.value_in_base_ccy.amount == Decimal("2025.00")


def test_valuation_trust_snapshot_mode(market_data):
    """Test trusting the provided MV over calculated."""
    # Market says 1500, but snapshot says 2000
    pos = Position(
        instrument_id="AAPL",
        quantity=Decimal("10"),
        market_value=Money(amount=Decimal("2000.00"), currency="USD"),
    )
    options = EngineOptions(valuation_mode=ValuationMode.TRUST_SNAPSHOT)
    dq = {}

    summary = ValuationService.value_position(pos, market_data, "SGD", options, dq)

    assert summary.value_in_instrument_ccy.amount == Decimal("2000.00")
    assert summary.value_in_base_ccy.amount == Decimal("2700.00")  # 2000 * 1.35


def test_valuation_zero_price_handling(market_data):
    """Test handling of assets with 0 price (e.g. rights, expired options)."""
    market_data.prices.append(
        Price(instrument_id="WORTHLESS", price=Decimal("0.0"), currency="USD")
    )
    pos = Position(instrument_id="WORTHLESS", quantity=Decimal("1000"))

    dq = {}
    summary = ValuationService.value_position(
        pos, market_data, "USD", EngineOptions(valuation_mode=ValuationMode.CALCULATED), dq
    )

    assert summary.value_in_base_ccy.amount == Decimal("0")


def test_valuation_missing_fx_logging(market_data):
    """Test that missing FX rates are logged to DQ."""
    market_data.prices.append(
        Price(instrument_id="NINTENDO", price=Decimal("5000"), currency="JPY")
    )
    pos = Position(instrument_id="NINTENDO", quantity=Decimal("100"))

    # No JPY/USD rate in market_data
    dq = {}
    # We call build_simulated_state indirectly via a mock portfolio context if strictly unit testing,
    # but here we test the Service directly. Service returns 0 for base val if FX missing.

    summary = ValuationService.value_position(
        pos, market_data, "USD", EngineOptions(valuation_mode=ValuationMode.CALCULATED), dq
    )

    assert summary.value_in_base_ccy.amount == Decimal("0")
    # Note: Service itself doesn't append to DQ, the caller (engine/build_simulated_state) does.
    # Let's verify build_simulated_state does it.

    from src.core.models import PortfolioSnapshot

    pf = PortfolioSnapshot(portfolio_id="p1", base_currency="USD", positions=[pos])
    warns = []

    state = build_simulated_state(pf, market_data, [], dq, warns)

    assert "JPY/USD" in dq["fx_missing"]
