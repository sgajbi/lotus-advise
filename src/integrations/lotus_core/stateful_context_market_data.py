from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from src.core.portfolio_models import FxRate, Price
from src.integrations.lotus_core.stateful_context_payload_values import (
    decimal_or_none,
    is_cash_asset_class,
    mapping_rows,
    normalized_text,
)


class InvalidLotusCoreFxRateError(ValueError):
    pass


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
    price_fields = _price_fields_from_position(raw_position)
    if price_fields is None:
        return None
    instrument_id, price, currency = price_fields
    return Price(instrument_id=instrument_id, price=price, currency=currency)


def _price_fields_from_position(raw_position: dict[str, Any]) -> tuple[str, Decimal, str] | None:
    instrument_id = normalized_text(raw_position.get("security_id"))
    currency = normalized_text(raw_position.get("currency"))
    valuation = raw_position.get("valuation")
    if not isinstance(valuation, dict) or not instrument_id or not currency:
        return None
    price = decimal_or_none(valuation.get("market_price"))
    if price is None:
        return None
    return instrument_id, price, currency


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
    fx_rate = _fx_rate_from_values(
        from_currency=from_currency,
        to_currency=to_currency,
        numerator=numerator,
        denominator=denominator,
    )
    if fx_rate is not None:
        fx_by_pair[fx_rate.pair] = fx_rate


def _fx_rate_from_values(
    *,
    from_currency: str,
    to_currency: str,
    numerator: Any,
    denominator: Any,
) -> FxRate | None:
    if not _has_distinct_currency_pair(from_currency, to_currency):
        return None
    decimal_inputs = _decimal_rate_inputs(numerator=numerator, denominator=denominator)
    if decimal_inputs is None:
        return None
    numerator_decimal, denominator_decimal = decimal_inputs
    return fx_rate_from_source_value(
        pair=f"{from_currency}/{to_currency}",
        rate=numerator_decimal / denominator_decimal,
    )


def fx_rate_from_source_value(*, pair: str, rate: Any) -> FxRate | None:
    if not _explicit_rate_value(rate):
        return None
    fx_rate = decimal_or_none(rate)
    if fx_rate is None:
        raise InvalidLotusCoreFxRateError("LOTUS_CORE_STATEFUL_FX_INVALID")
    try:
        return FxRate(pair=pair, rate=fx_rate)
    except ValueError as exc:
        raise InvalidLotusCoreFxRateError("LOTUS_CORE_STATEFUL_FX_INVALID") from exc


def _has_distinct_currency_pair(from_currency: str, to_currency: str) -> bool:
    return bool(from_currency and to_currency and from_currency != to_currency)


def _decimal_rate_inputs(*, numerator: Any, denominator: Any) -> tuple[Decimal, Decimal] | None:
    if not _rate_values_present(numerator=numerator, denominator=denominator):
        return None
    numerator_decimal = _required_decimal_rate_value(numerator)
    denominator_decimal = _required_decimal_rate_value(denominator)
    _require_non_zero_denominator(denominator_decimal)
    return numerator_decimal, denominator_decimal


def _rate_values_present(*, numerator: Any, denominator: Any) -> bool:
    return _explicit_rate_value(numerator) and _explicit_rate_value(denominator)


def _required_decimal_rate_value(value: Any) -> Decimal:
    rate_value = decimal_or_none(value)
    if rate_value is None:
        raise InvalidLotusCoreFxRateError("LOTUS_CORE_STATEFUL_FX_INVALID")
    return cast(Decimal, rate_value)


def _require_non_zero_denominator(denominator: Decimal) -> None:
    if denominator == Decimal("0"):
        raise InvalidLotusCoreFxRateError("LOTUS_CORE_STATEFUL_FX_INVALID")


def _explicit_rate_value(value: Any) -> bool:
    return value is not None and value != ""
