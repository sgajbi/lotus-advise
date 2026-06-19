from __future__ import annotations

from typing import Any

from src.core.portfolio_models import CashBalance, Money, Position
from src.integrations.lotus_core.stateful_context_market_data import (
    build_prices,
    derive_fx_rates,
)
from src.integrations.lotus_core.stateful_context_payload_values import (
    decimal_or_none,
    is_cash_asset_class,
    mapping_rows,
    normalized_text,
)
from src.integrations.lotus_core.stateful_context_shelf_entries import (
    build_shelf_entries,
    shelf_attributes_from_payload,
)

__all__ = [
    "build_cash_balances",
    "build_positions",
    "build_prices",
    "build_shelf_entries",
    "decimal_or_none",
    "derive_fx_rates",
    "shelf_attributes_from_payload",
]


def build_cash_balances(cash_payload: dict[str, Any]) -> list[CashBalance]:
    balances: list[CashBalance] = []
    for account in mapping_rows(cash_payload, "cash_accounts"):
        currency = normalized_text(account.get("account_currency"))
        if not currency:
            continue
        amount = decimal_or_none(account.get("balance_account_currency"))
        if amount is None:
            continue
        balances.append(CashBalance(currency=currency, amount=amount))
    return balances


def build_positions(
    positions_payload: dict[str, Any], *, portfolio_base_currency: str
) -> list[Position]:
    positions: list[Position] = []
    for raw_position in mapping_rows(positions_payload, "positions"):
        position = _position_from_payload(
            raw_position,
            portfolio_base_currency=portfolio_base_currency,
        )
        if position is not None:
            positions.append(position)
    return positions


def _position_from_payload(
    raw_position: dict[str, Any], *, portfolio_base_currency: str
) -> Position | None:
    if is_cash_asset_class(raw_position.get("asset_class")):
        return None
    instrument_id = normalized_text(raw_position.get("security_id"))
    quantity = decimal_or_none(raw_position.get("quantity"))
    if not instrument_id or quantity is None:
        return None
    return Position(
        instrument_id=instrument_id,
        quantity=quantity,
        market_value=_market_value_from_payload(
            raw_position,
            portfolio_base_currency=portfolio_base_currency,
        ),
    )


def _market_value_from_payload(
    raw_position: dict[str, Any], *, portfolio_base_currency: str
) -> Money | None:
    valuation = raw_position.get("valuation")
    if not isinstance(valuation, dict):
        return None
    market_value_amount = decimal_or_none(valuation.get("market_value"))
    if market_value_amount is None:
        return None
    return Money(
        amount=market_value_amount,
        currency=portfolio_base_currency,
    )
