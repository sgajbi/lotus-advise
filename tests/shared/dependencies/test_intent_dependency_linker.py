from decimal import Decimal

from src.core.common.intent_dependencies import link_buy_intent_dependencies
from src.core.models import IntentRationale, Money, SecurityTradeIntent


def _trade(*, intent_id: str, side: str, instrument_id: str, currency: str) -> SecurityTradeIntent:
    return SecurityTradeIntent(
        intent_id=intent_id,
        side=side,
        instrument_id=instrument_id,
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency=currency),
        notional_base=Money(amount=Decimal("100"), currency="USD"),
        rationale=IntentRationale(code="TEST", message="test"),
        dependencies=[],
        constraints_applied=[],
    )


def test_link_buy_intent_dependencies_adds_fx_and_sell_dependencies_in_order():
    sell = _trade(intent_id="oi_1", side="SELL", instrument_id="EQ_OLD", currency="USD")
    buy = _trade(intent_id="oi_2", side="BUY", instrument_id="EQ_NEW", currency="USD")

    link_buy_intent_dependencies(
        [sell, buy],
        fx_intent_id_by_currency={"USD": "oi_fx_1"},
        include_same_currency_sell_dependency=True,
    )

    assert buy.dependencies == ["oi_fx_1", "oi_1"]


def test_link_buy_intent_dependencies_does_not_duplicate_existing_values():
    sell = _trade(intent_id="oi_1", side="SELL", instrument_id="EQ_OLD", currency="USD")
    buy = _trade(intent_id="oi_2", side="BUY", instrument_id="EQ_NEW", currency="USD")
    buy.dependencies = ["oi_fx_1", "oi_1"]

    link_buy_intent_dependencies(
        [sell, buy],
        fx_intent_id_by_currency={"USD": "oi_fx_1"},
        include_same_currency_sell_dependency=True,
    )

    assert buy.dependencies == ["oi_fx_1", "oi_1"]
