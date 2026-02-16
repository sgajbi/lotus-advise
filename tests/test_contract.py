"""
FILE: tests/test_contract.py
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.core.models import (
    EngineOptions,
    FxSpotIntent,
    Money,
    SecurityTradeIntent,
    ValuationMode,
)


def test_engine_options_defaults():
    """RFC-0007A: Validation Mode must default to CALCULATED."""
    opts = EngineOptions()
    assert opts.valuation_mode == ValuationMode.CALCULATED
    assert opts.allow_restricted is False


def test_security_trade_intent_valid():
    """Valid Security Trade."""
    intent = SecurityTradeIntent(
        intent_id="oi_1",
        instrument_id="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        notional=Money(amount=Decimal("1500"), currency="USD"),
        notional_base=Money(amount=Decimal("2000"), currency="SGD"),
    )
    assert intent.intent_type == "SECURITY_TRADE"
    assert intent.instrument_id == "AAPL"


def test_fx_spot_intent_valid():
    """Valid FX Spot."""
    intent = FxSpotIntent(
        intent_id="oi_fx_1",
        pair="USD/SGD",
        buy_currency="USD",
        buy_amount=Decimal("1000"),
        sell_currency="SGD",
        sell_amount_estimated=Decimal("1350"),
    )
    assert intent.intent_type == "FX_SPOT"
    # Ensure no extra fields like instrument_id are allowed/present implicitly
    assert not hasattr(intent, "instrument_id")


def test_intent_discrimination():
    """
    Ensure Pydantic strictly validates the discriminated union.
    If we try to pass an FX intent structure as a Security intent, it should fail.
    """
    with pytest.raises(ValidationError) as exc:
        SecurityTradeIntent(
            intent_id="fail_1",
            side="BUY",
            # Missing instrument_id
            quantity=Decimal("10"),
        )
    assert "Field required" in str(exc.value)
    assert "instrument_id" in str(exc.value)


def test_fx_intent_requirements():
    """FX Intent must have pair and amounts."""
    with pytest.raises(ValidationError) as exc:
        FxSpotIntent(
            intent_id="fail_fx",
            # Missing pair
            buy_currency="USD",
            buy_amount=Decimal("100"),
            sell_currency="SGD",
            sell_amount_estimated=Decimal("130"),
        )
    assert "Field required" in str(exc.value)
    assert "pair" in str(exc.value)
