from decimal import Decimal

from src.core.common.simulation_shared import ensure_cash_balance
from src.core.models import IntentRationale, Money, SecurityTradeIntent
from src.core.valuation import get_fx_rate


def apply_proposal_cash_flow(after_pf, cash_flow):
    cash_entry = ensure_cash_balance(after_pf, cash_flow.currency)
    cash_entry.amount += cash_flow.amount


def build_proposal_security_trade_intent(
    *,
    trade,
    market_data,
    base_currency,
    intent_id,
    dq_log,
):
    price_ent = next(
        (p for p in market_data.prices if p.instrument_id == trade.instrument_id), None
    )
    if not price_ent:
        dq_log["price_missing"].append(trade.instrument_id)
        return None, None

    if trade.quantity is not None:
        quantity = trade.quantity
        notional_amount = quantity * price_ent.price
    else:
        if trade.notional.currency != price_ent.currency:
            return None, "PROPOSAL_INVALID_TRADE_INPUT"
        notional_amount = trade.notional.amount
        quantity = notional_amount / price_ent.price

    notional_base = None
    fx_rate = get_fx_rate(market_data, price_ent.currency, base_currency)
    if fx_rate is None:
        dq_log["fx_missing"].append(f"{price_ent.currency}/{base_currency}")
    else:
        notional_base = Money(amount=notional_amount * fx_rate, currency=base_currency)

    return (
        SecurityTradeIntent(
            intent_id=intent_id,
            side=trade.side,
            instrument_id=trade.instrument_id,
            quantity=quantity,
            notional=Money(amount=notional_amount, currency=price_ent.currency),
            notional_base=notional_base,
            rationale=IntentRationale(code="MANUAL_PROPOSAL", message="Advisor proposed trade"),
            dependencies=[],
            constraints_applied=[],
        ),
        None,
    )


def expected_cash_delta_base(portfolio, market_data, cash_flows, dq_log):
    total = Decimal("0")
    for cash_flow in cash_flows:
        fx_rate = get_fx_rate(market_data, cash_flow.currency, portfolio.base_currency)
        if fx_rate is None:
            dq_log["fx_missing"].append(f"{cash_flow.currency}/{portfolio.base_currency}")
            continue
        total += cash_flow.amount * fx_rate
    return total
