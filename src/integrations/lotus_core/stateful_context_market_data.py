from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.core.portfolio_models import FxRate, Price
from src.integrations.lotus_core.stateful_context_payload_values import (
    decimal_or_none,
    is_cash_asset_class,
    mapping_rows,
    normalized_text,
)


def build_prices(positions_payload: dict[str, Any]) -> list[Price]:
    price_map: dict[str, Price] = {}
    for raw_position in mapping_rows(positions_payload, "positions"):
        price = _price_from_position(raw_position)
        if price is not None:
            price_map[price.instrument_id] = price
    return list(price_map.values())


def _price_from_position(raw_position: dict[str, Any]) -> Price | None:
    if is_cash_asset_class(raw_position.get("asset_class")):
        return None
    instrument_id = normalized_text(raw_position.get("security_id"))
    currency = normalized_text(raw_position.get("currency"))
    valuation = raw_position.get("valuation")
    if not isinstance(valuation, dict) or not instrument_id or not currency:
        return None
    price = decimal_or_none(valuation.get("market_price"))
    if price is None:
        return None
    return Price(instrument_id=instrument_id, price=price, currency=currency)


def derive_fx_rates(
    *,
    portfolio_base_currency: str,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
) -> list[FxRate]:
    fx_by_pair: dict[str, FxRate] = {}
    for raw_position in mapping_rows(positions_payload, "positions"):
        _capture_position_fx_rate(
            fx_by_pair,
            raw_position=raw_position,
            portfolio_base_currency=portfolio_base_currency,
        )
    for account in mapping_rows(cash_payload, "cash_accounts"):
        _capture_cash_fx_rate(
            fx_by_pair,
            account=account,
            portfolio_base_currency=portfolio_base_currency,
        )
    return list(fx_by_pair.values())


def _capture_position_fx_rate(
    fx_by_pair: dict[str, FxRate],
    *,
    raw_position: dict[str, Any],
    portfolio_base_currency: str,
) -> None:
    valuation = raw_position.get("valuation")
    if not isinstance(valuation, dict):
        return
    _capture_rate(
        fx_by_pair,
        from_currency=normalized_text(raw_position.get("currency")),
        to_currency=portfolio_base_currency,
        numerator=valuation.get("market_value"),
        denominator=valuation.get("market_value_local"),
    )


def _capture_cash_fx_rate(
    fx_by_pair: dict[str, FxRate],
    *,
    account: dict[str, Any],
    portfolio_base_currency: str,
) -> None:
    _capture_rate(
        fx_by_pair,
        from_currency=normalized_text(account.get("account_currency")),
        to_currency=portfolio_base_currency,
        numerator=account.get("balance_portfolio_currency"),
        denominator=account.get("balance_account_currency"),
    )


def _capture_rate(
    fx_by_pair: dict[str, FxRate],
    *,
    from_currency: str,
    to_currency: str,
    numerator: Any,
    denominator: Any,
) -> None:
    if not from_currency or not to_currency or from_currency == to_currency:
        return
    numerator_decimal = decimal_or_none(numerator)
    denominator_decimal = decimal_or_none(denominator)
    if (
        numerator_decimal is None
        or denominator_decimal is None
        or denominator_decimal == Decimal("0")
    ):
        return
    pair = f"{from_currency}/{to_currency}"
    fx_by_pair[pair] = FxRate(
        pair=pair,
        rate=numerator_decimal / denominator_decimal,
    )
