from decimal import Decimal

from src.core.advisory.intents import build_proposal_security_trade_intent
from src.core.portfolio_models import Money
from src.core.proposal_request_models import ProposedTrade
from tests.shared.factories import market_data_snapshot, price


def _dq_log() -> dict[str, list[str]]:
    return {"price_missing": [], "fx_missing": []}


def test_build_proposal_security_trade_intent_sizes_quantity_trade_with_base_notional():
    dq_log = _dq_log()
    market_data = market_data_snapshot(
        prices=[price("US_EQ", "100", "USD")],
        fx_rates=[{"pair": "USD/SGD", "rate": "1.35"}],
    )

    intent, error_code = build_proposal_security_trade_intent(
        trade=ProposedTrade(side="BUY", instrument_id="US_EQ", quantity=Decimal("10")),
        market_data=market_data,
        base_currency="SGD",
        intent_id="trade_1",
        dq_log=dq_log,
    )

    assert error_code is None
    assert intent is not None
    assert intent.quantity == Decimal("10")
    assert intent.notional == Money(amount=Decimal("1000"), currency="USD")
    assert intent.notional_base == Money(amount=Decimal("1350.00"), currency="SGD")
    assert dq_log == {"price_missing": [], "fx_missing": []}


def test_build_proposal_security_trade_intent_rejects_notional_currency_mismatch():
    dq_log = _dq_log()
    market_data = market_data_snapshot(prices=[price("US_EQ", "100", "USD")], fx_rates=[])

    intent, error_code = build_proposal_security_trade_intent(
        trade=ProposedTrade(
            side="BUY",
            instrument_id="US_EQ",
            notional=Money(amount=Decimal("1000"), currency="EUR"),
        ),
        market_data=market_data,
        base_currency="USD",
        intent_id="trade_1",
        dq_log=dq_log,
    )

    assert intent is None
    assert error_code == "PROPOSAL_INVALID_TRADE_INPUT"
    assert dq_log == {"price_missing": [], "fx_missing": []}


def test_build_proposal_security_trade_intent_records_missing_fx_and_preserves_intent():
    dq_log = _dq_log()
    market_data = market_data_snapshot(prices=[price("US_EQ", "100", "USD")], fx_rates=[])

    intent, error_code = build_proposal_security_trade_intent(
        trade=ProposedTrade(side="BUY", instrument_id="US_EQ", quantity=Decimal("2")),
        market_data=market_data,
        base_currency="SGD",
        intent_id="trade_1",
        dq_log=dq_log,
    )

    assert error_code is None
    assert intent is not None
    assert intent.notional == Money(amount=Decimal("200"), currency="USD")
    assert intent.notional_base is None
    assert dq_log == {"price_missing": [], "fx_missing": ["USD/SGD"]}
