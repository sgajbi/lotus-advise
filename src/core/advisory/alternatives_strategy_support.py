from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal
from typing import cast

from src.core.advisory.alternatives_models import ProposalAlternativesConstraints
from src.core.advisory.alternatives_strategy_models import (
    AlternativeStrategyInputs,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
)

_MONEY_STEP = Decimal("0.01")


def candidate_id(*, objective: str, portfolio_id: str, pivot: str) -> str:
    normalized_pivot = pivot.lower().replace("/", "_")
    return f"alt_{objective.lower()}_{portfolio_id.lower()}_{normalized_pivot}"


def largest_sellable_position(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
    preferred_currency: str | None = None,
    exclude_currencies: set[str] | None = None,
) -> StrategyPosition | None:
    blocked_ids = set(constraints.preserve_holdings) | set(constraints.do_not_sell)
    candidates = [
        position
        for position in inputs.positions
        if position.quantity > Decimal("0")
        and position.instrument_id not in blocked_ids
        and (preferred_currency is None or position.currency == preferred_currency)
        and (exclude_currencies is None or position.currency not in exclude_currencies)
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda position: (-position_rank_value(position), position.instrument_id),
    )[0]


def preferred_buy_instrument(
    *,
    inputs: AlternativeStrategyInputs,
    constraints: ProposalAlternativesConstraints,
    excluded_ids: set[str],
    preferred_currency: str | None = None,
) -> StrategyPosition | None:
    shelf_lookup = approved_shelf_lookup(inputs)
    blocked_ids = buy_blocked_instrument_ids(
        constraints=constraints,
        excluded_ids=excluded_ids,
    )
    approved_positions = sorted(
        (
            position
            for position in inputs.positions
            if existing_position_is_preferred_buy_candidate(
                position=position,
                shelf_lookup=shelf_lookup,
                blocked_ids=blocked_ids,
                preferred_currency=preferred_currency,
            )
        ),
        key=lambda position: (position_rank_value(position), position.instrument_id),
    )
    if approved_positions:
        return approved_positions[0]

    return first_synthetic_buy_candidate(
        shelf_lookup=shelf_lookup,
        blocked_ids=blocked_ids,
        preferred_currency=preferred_currency,
    )


def approved_shelf_lookup(
    inputs: AlternativeStrategyInputs,
) -> dict[str, StrategyShelfInstrument]:
    return {
        instrument.instrument_id: instrument
        for instrument in inputs.shelf_instruments
        if instrument.status == "APPROVED"
    }


def buy_blocked_instrument_ids(
    *,
    constraints: ProposalAlternativesConstraints,
    excluded_ids: set[str],
) -> set[str]:
    return set(constraints.restricted_instruments) | set(constraints.do_not_buy) | excluded_ids


def existing_position_is_preferred_buy_candidate(
    *,
    position: StrategyPosition,
    shelf_lookup: dict[str, StrategyShelfInstrument],
    blocked_ids: set[str],
    preferred_currency: str | None,
) -> bool:
    return (
        position.instrument_id in shelf_lookup
        and position.instrument_id not in blocked_ids
        and (preferred_currency is None or position.currency == preferred_currency)
    )


def first_synthetic_buy_candidate(
    *,
    shelf_lookup: dict[str, StrategyShelfInstrument],
    blocked_ids: set[str],
    preferred_currency: str | None,
) -> StrategyPosition | None:
    synthetic_positions = sorted(
        (
            StrategyPosition(
                instrument_id=instrument_id,
                quantity=Decimal("0"),
                price=None,
                currency=preferred_currency,
            )
            for instrument_id in shelf_lookup
            if instrument_id not in blocked_ids
        ),
        key=lambda position: position.instrument_id,
    )
    return synthetic_positions[0] if synthetic_positions else None


def first_adjustable_trade(
    trades: tuple[StrategyTradeIntent, ...],
) -> StrategyTradeIntent | None:
    for trade in trades:
        if (trade.quantity is not None and trade.quantity > Decimal("1")) or (
            trade.notional_amount is not None and trade.notional_amount > Decimal("0.01")
        ):
            return trade
    return None


def reduced_trade_payload(trade: StrategyTradeIntent) -> dict[str, object] | None:
    if trade.quantity is not None:
        reduced_quantity = half_quantity(trade.quantity)
        if reduced_quantity is None:
            return None
        return {
            "intent_type": "SECURITY_TRADE",
            "side": trade.side,
            "instrument_id": trade.instrument_id,
            "quantity": decimal_string(reduced_quantity),
        }
    if trade.notional_amount is not None and trade.notional_currency is not None:
        reduced_notional = half_money(trade.notional_amount)
        if reduced_notional is None:
            return None
        return {
            "intent_type": "SECURITY_TRADE",
            "side": trade.side,
            "instrument_id": trade.instrument_id,
            "notional": {
                "amount": decimal_string(reduced_notional),
                "currency": trade.notional_currency,
            },
        }
    return None


def position_rank_value(position: StrategyPosition) -> Decimal:
    if position.price is None:
        return cast(Decimal, position.quantity)
    return cast(Decimal, position.quantity * position.price)


def half_quantity(quantity: Decimal) -> Decimal | None:
    if quantity <= Decimal("1"):
        return None
    halved = quantity / Decimal("2")
    reduced = halved.quantize(Decimal("1"), rounding=ROUND_DOWN)
    if reduced <= Decimal("0"):
        return None
    return reduced


def half_money(amount: Decimal) -> Decimal | None:
    if amount <= _MONEY_STEP:
        return None
    halved = (amount / Decimal("2")).quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)
    if halved <= Decimal("0"):
        return None
    return halved


def estimated_notional(price: Decimal | None, quantity: Decimal) -> Decimal | None:
    if price is None:
        return None
    return (price * quantity).quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)


def quantity_for_notional(
    required_notional: Decimal,
    price: Decimal,
    max_quantity: Decimal,
) -> Decimal | None:
    if required_notional <= Decimal("0"):
        return None
    required_quantity = (required_notional / price).quantize(Decimal("1"), rounding=ROUND_UP)
    if required_quantity <= Decimal("0") or required_quantity > max_quantity:
        return None
    return required_quantity


def decimal_string(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")
