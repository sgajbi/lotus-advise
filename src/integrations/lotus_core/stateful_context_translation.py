from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from src.core.models import CashBalance, FxRate, Money, Position, Price, ShelfEntry
from src.integrations.lotus_core.classification import (
    ClassificationTaxonomy,
    classification_supportability_attributes,
    normalized_optional_str,
    prefer_upstream_liquidity_tier,
    resolve_taxonomy_label,
)


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def shelf_attributes_from_payload(
    *,
    sector: Any = None,
    country: Any = None,
    product_type: Any = None,
    rating: Any = None,
    ultimate_parent_issuer_id: Any = None,
    ultimate_parent_issuer_name: Any = None,
) -> dict[str, str]:
    attributes = {"source": "LOTUS_CORE_STATEFUL_CONTEXT"}
    optional_values = {
        "sector": sector,
        "country": country,
        "product_type": product_type,
        "rating": rating,
        "ultimate_parent_issuer_id": ultimate_parent_issuer_id,
        "ultimate_parent_issuer_name": ultimate_parent_issuer_name,
    }
    for key, raw_value in optional_values.items():
        value = str(raw_value or "").strip()
        if value:
            attributes[key] = value
    return attributes


def build_cash_balances(cash_payload: dict[str, Any]) -> list[CashBalance]:
    balances: list[CashBalance] = []
    for account in cash_payload.get("cash_accounts", []):
        if not isinstance(account, dict):
            continue
        currency = str(account.get("account_currency") or "").strip()
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
    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        asset_class = str(raw_position.get("asset_class") or "").strip().lower()
        if asset_class == "cash":
            continue
        instrument_id = str(raw_position.get("security_id") or "").strip()
        quantity = decimal_or_none(raw_position.get("quantity"))
        if not instrument_id or quantity is None:
            continue
        market_value: Money | None = None
        valuation = raw_position.get("valuation")
        if isinstance(valuation, dict):
            market_value_amount = decimal_or_none(valuation.get("market_value"))
            if market_value_amount is not None:
                market_value = Money(
                    amount=market_value_amount,
                    currency=portfolio_base_currency,
                )
        positions.append(
            Position(
                instrument_id=instrument_id,
                quantity=quantity,
                market_value=market_value,
            )
        )
    return positions


def build_prices(positions_payload: dict[str, Any]) -> list[Price]:
    price_map: dict[str, Price] = {}
    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        asset_class = str(raw_position.get("asset_class") or "").strip().lower()
        if asset_class == "cash":
            continue
        instrument_id = str(raw_position.get("security_id") or "").strip()
        currency = str(raw_position.get("currency") or "").strip()
        valuation = raw_position.get("valuation")
        if not isinstance(valuation, dict) or not instrument_id or not currency:
            continue
        price = decimal_or_none(valuation.get("market_price"))
        if price is None:
            continue
        price_map[instrument_id] = Price(
            instrument_id=instrument_id,
            price=price,
            currency=currency,
        )
    return list(price_map.values())


def derive_fx_rates(
    *,
    portfolio_base_currency: str,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
) -> list[FxRate]:
    fx_by_pair: dict[str, FxRate] = {}

    def _capture_rate(
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
        fx_by_pair[pair] = FxRate(pair=pair, rate=(numerator_decimal / denominator_decimal))

    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        position_currency = str(raw_position.get("currency") or "").strip()
        valuation = raw_position.get("valuation")
        if not isinstance(valuation, dict):
            continue
        _capture_rate(
            position_currency,
            portfolio_base_currency,
            valuation.get("market_value"),
            valuation.get("market_value_local"),
        )

    for account in cash_payload.get("cash_accounts", []):
        if not isinstance(account, dict):
            continue
        _capture_rate(
            str(account.get("account_currency") or "").strip(),
            portfolio_base_currency,
            account.get("balance_portfolio_currency"),
            account.get("balance_account_currency"),
        )

    return list(fx_by_pair.values())


def build_shelf_entries(
    *,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
    enrichment_by_instrument_id: dict[str, dict[str, Any]] | None = None,
    classification_taxonomy: ClassificationTaxonomy | None = None,
) -> list[ShelfEntry]:
    shelf_by_instrument: dict[str, ShelfEntry] = {}

    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        instrument_id = str(raw_position.get("security_id") or "").strip()
        if not instrument_id:
            continue
        asset_class, asset_class_source = resolve_taxonomy_label(
            raw_position.get("asset_class"),
            dimension_name="asset_class",
            taxonomy=classification_taxonomy,
        )
        product_type, product_type_source = resolve_taxonomy_label(
            raw_position.get("product_type"),
            dimension_name="product_type",
            taxonomy=classification_taxonomy,
            preserve_raw_when_ungoverned=True,
        )
        enrichment_row = (enrichment_by_instrument_id or {}).get(instrument_id, {})
        shelf_by_instrument[instrument_id] = ShelfEntry(
            instrument_id=instrument_id,
            status="APPROVED",
            asset_class=asset_class,
            issuer_id=normalized_optional_str(
                raw_position.get("issuer_id")
                if raw_position.get("issuer_id") is not None
                else enrichment_row.get("issuer_id")
            ),
            liquidity_tier=prefer_upstream_liquidity_tier(
                raw_liquidity_tier=raw_position.get("liquidity_tier"),
                enrichment_liquidity_tier=enrichment_row.get("liquidity_tier"),
                asset_class=asset_class,
                product_type=product_type,
                sector=raw_position.get("sector"),
                rating=raw_position.get("rating"),
            ),
            attributes=(
                shelf_attributes_from_payload(
                    sector=raw_position.get("sector"),
                    country=raw_position.get("country_of_risk"),
                    product_type=product_type,
                    rating=raw_position.get("rating"),
                    ultimate_parent_issuer_id=(
                        raw_position.get("ultimate_parent_issuer_id")
                        if raw_position.get("ultimate_parent_issuer_id") is not None
                        else enrichment_row.get("ultimate_parent_issuer_id")
                    ),
                    ultimate_parent_issuer_name=(
                        raw_position.get("ultimate_parent_issuer_name")
                        if raw_position.get("ultimate_parent_issuer_name") is not None
                        else enrichment_row.get("ultimate_parent_issuer_name")
                    ),
                )
                | classification_supportability_attributes(
                    asset_class_source=asset_class_source,
                    product_type_source=product_type_source,
                    taxonomy=classification_taxonomy,
                )
            ),
        )

    for account in cash_payload.get("cash_accounts", []):
        if not isinstance(account, dict):
            continue
        instrument_id = str(
            account.get("instrument_id") or account.get("security_id") or ""
        ).strip()
        if not instrument_id:
            continue
        shelf_by_instrument[instrument_id] = ShelfEntry(
            instrument_id=instrument_id,
            status="APPROVED",
            asset_class="CASH",
            issuer_id=normalized_optional_str(account.get("issuer_id")),
            liquidity_tier=prefer_upstream_liquidity_tier(
                raw_liquidity_tier=account.get("liquidity_tier"),
                asset_class="CASH",
                product_type="Cash",
                sector=None,
                rating=None,
            ),
            attributes=shelf_attributes_from_payload(product_type="Cash"),
        )

    return list(shelf_by_instrument.values())
