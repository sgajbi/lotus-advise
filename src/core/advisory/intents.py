from decimal import Decimal
from typing import Any, NamedTuple

from src.core.common.simulation_shared import ensure_cash_balance
from src.core.order_intent_models import IntentRationale, SecurityTradeIntent
from src.core.portfolio_models import Money, Price
from src.core.valuation import get_fx_rate


class _ResolvedTradeNotional(NamedTuple):
    quantity: Decimal
    amount: Decimal
    currency: str


def apply_proposal_cash_flow(after_pf: Any, cash_flow: Any) -> None:
    cash_entry = ensure_cash_balance(after_pf, cash_flow.currency)
    cash_entry.amount += cash_flow.amount


def build_proposal_security_trade_intent(
    *,
    trade: Any,
    market_data: Any,
    base_currency: str,
    intent_id: str,
    dq_log: dict[str, list[str]],
) -> tuple[SecurityTradeIntent | None, str | None]:
    price = _price_for_trade(market_data, trade.instrument_id)
    if not price:
        dq_log["price_missing"].append(trade.instrument_id)
        return None, None

    resolved_notional = _resolve_trade_notional(trade=trade, price=price)
    if resolved_notional is None:
        return None, "PROPOSAL_INVALID_TRADE_INPUT"

    notional_base = _notional_base_money(
        market_data=market_data,
        notional=resolved_notional,
        base_currency=base_currency,
        dq_log=dq_log,
    )

    return (
        SecurityTradeIntent(
            intent_id=intent_id,
            side=trade.side,
            instrument_id=trade.instrument_id,
            quantity=resolved_notional.quantity,
            notional=Money(amount=resolved_notional.amount, currency=resolved_notional.currency),
            notional_base=notional_base,
            rationale=IntentRationale(code="MANUAL_PROPOSAL", message="Advisor proposed trade"),
            dependencies=[],
            constraints_applied=[],
        ),
        None,
    )


def _price_for_trade(market_data: Any, instrument_id: str) -> Price | None:
    return next((p for p in market_data.prices if p.instrument_id == instrument_id), None)


def _resolve_trade_notional(*, trade: Any, price: Price) -> _ResolvedTradeNotional | None:
    if trade.quantity is not None:
        return _ResolvedTradeNotional(
            quantity=trade.quantity,
            amount=trade.quantity * price.price,
            currency=price.currency,
        )
    if trade.notional.currency != price.currency:
        return None
    return _ResolvedTradeNotional(
        quantity=trade.notional.amount / price.price,
        amount=trade.notional.amount,
        currency=price.currency,
    )


def _notional_base_money(
    *,
    market_data: Any,
    notional: _ResolvedTradeNotional,
    base_currency: str,
    dq_log: dict[str, list[str]],
) -> Money | None:
    fx_rate = get_fx_rate(market_data, notional.currency, base_currency)
    if fx_rate is None:
        dq_log["fx_missing"].append(f"{notional.currency}/{base_currency}")
        return None
    return Money(amount=notional.amount * fx_rate, currency=base_currency)


def expected_cash_delta_base(
    portfolio: Any,
    market_data: Any,
    cash_flows: list[Any],
    dq_log: dict[str, list[str]],
) -> Decimal:
    total = Decimal("0")
    for cash_flow in cash_flows:
        fx_rate = get_fx_rate(market_data, cash_flow.currency, portfolio.base_currency)
        if fx_rate is None:
            dq_log["fx_missing"].append(f"{cash_flow.currency}/{portfolio.base_currency}")
            continue
        total += cash_flow.amount * fx_rate
    return total
