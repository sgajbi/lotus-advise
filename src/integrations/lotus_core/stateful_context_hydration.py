from __future__ import annotations

from typing import Any, Callable, cast

import httpx

from src.core.models import FxRate, Price, ProposalSimulateRequest, ShelfEntry
from src.integrations.lotus_core.classification import (
    ClassificationTaxonomy,
    classification_supportability_attributes,
    normalized_optional_str,
    prefer_upstream_liquidity_tier,
    resolve_taxonomy_label,
)
from src.integrations.lotus_core.stateful_context_cache import (
    FX_LOOKUP_CACHE,
    INSTRUMENT_LOOKUP_CACHE,
    PRICE_LOOKUP_CACHE,
)
from src.integrations.lotus_core.stateful_context_routes import (
    FX_RATES_PATH,
    INSTRUMENTS_PATH,
    PRICES_PATH,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    fetch_classification_taxonomy,
    fetch_instrument_enrichment_bulk,
    fetch_json_with_cache,
)
from src.integrations.lotus_core.stateful_context_translation import (
    decimal_or_none,
    shelf_attributes_from_payload,
)

HttpClientFactory = Callable[[httpx.Timeout], httpx.Client]


def select_latest_dated_row(
    rows: list[dict[str, Any]],
    *,
    date_key: str,
    as_of: str,
) -> dict[str, Any] | None:
    dated_rows = [
        row for row in rows if isinstance(row, dict) and isinstance(row.get(date_key), str)
    ]
    if not dated_rows:
        return None
    eligible_rows = [row for row in dated_rows if row[date_key] <= as_of]
    target_rows = eligible_rows or dated_rows
    return max(target_rows, key=lambda row: str(row[date_key]))


def has_fx_pair(
    *,
    fx_rates: list[FxRate],
    from_currency: str,
    to_currency: str,
) -> bool:
    direct_pair = f"{from_currency}/{to_currency}"
    inverse_pair = f"{to_currency}/{from_currency}"
    return any(rate.pair in {direct_pair, inverse_pair} for rate in fx_rates)


def select_instrument_row(instrument_payload: dict[str, Any]) -> dict[str, Any] | None:
    instrument_rows = instrument_payload.get("instruments")
    if not isinstance(instrument_rows, list) or not instrument_rows:
        return None
    instrument_row = instrument_rows[0]
    return instrument_row if isinstance(instrument_row, dict) else None


def select_latest_price_row(
    *,
    price_payload: dict[str, Any],
    as_of: str,
) -> dict[str, Any] | None:
    price_rows = price_payload.get("prices")
    if not isinstance(price_rows, list):
        return None
    return select_latest_dated_row(price_rows, date_key="price_date", as_of=as_of)


def select_latest_fx_row(
    *,
    fx_payload: dict[str, Any],
    as_of: str,
) -> dict[str, Any] | None:
    fx_rows = fx_payload.get("rates")
    if not isinstance(fx_rows, list):
        return None
    return select_latest_dated_row(fx_rows, date_key="rate_date", as_of=as_of)


def append_price_if_missing(
    *,
    simulate_request: ProposalSimulateRequest,
    instrument_id: str,
    instrument_currency: str,
    latest_price_row: dict[str, Any],
) -> None:
    if any(
        price.instrument_id == instrument_id
        for price in simulate_request.market_data_snapshot.prices
    ):
        return
    price_value = decimal_or_none(latest_price_row.get("price"))
    if price_value is None:
        return
    simulate_request.market_data_snapshot.prices.append(
        Price(
            instrument_id=instrument_id,
            price=price_value,
            currency=instrument_currency,
        )
    )


def append_shelf_entry_if_missing(
    *,
    simulate_request: ProposalSimulateRequest,
    instrument_id: str,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any] | None = None,
    classification_taxonomy: ClassificationTaxonomy | None = None,
) -> None:
    if any(entry.instrument_id == instrument_id for entry in simulate_request.shelf_entries):
        return
    asset_class, asset_class_source = resolve_taxonomy_label(
        instrument_row.get("asset_class"),
        dimension_name="asset_class",
        taxonomy=classification_taxonomy,
    )
    product_type, product_type_source = resolve_taxonomy_label(
        instrument_row.get("product_type"),
        dimension_name="product_type",
        taxonomy=classification_taxonomy,
        preserve_raw_when_ungoverned=True,
    )
    simulate_request.shelf_entries.append(
        ShelfEntry(
            instrument_id=instrument_id,
            status="APPROVED",
            asset_class=asset_class,
            issuer_id=normalized_optional_str(
                instrument_row.get("issuer_id")
                if instrument_row.get("issuer_id") is not None
                else (enrichment_row or {}).get("issuer_id")
            ),
            liquidity_tier=prefer_upstream_liquidity_tier(
                raw_liquidity_tier=instrument_row.get("liquidity_tier"),
                enrichment_liquidity_tier=(enrichment_row or {}).get("liquidity_tier"),
                asset_class=asset_class,
                product_type=product_type,
                sector=instrument_row.get("sector"),
                rating=instrument_row.get("rating"),
            ),
            attributes=(
                shelf_attributes_from_payload(
                    sector=instrument_row.get("sector"),
                    country=instrument_row.get("country_of_risk"),
                    product_type=product_type,
                    rating=instrument_row.get("rating"),
                    ultimate_parent_issuer_id=(
                        instrument_row.get("ultimate_parent_issuer_id")
                        if instrument_row.get("ultimate_parent_issuer_id") is not None
                        else (enrichment_row or {}).get("ultimate_parent_issuer_id")
                    ),
                    ultimate_parent_issuer_name=(
                        instrument_row.get("ultimate_parent_issuer_name")
                        if instrument_row.get("ultimate_parent_issuer_name") is not None
                        else (enrichment_row or {}).get("ultimate_parent_issuer_name")
                    ),
                )
                | classification_supportability_attributes(
                    asset_class_source=asset_class_source,
                    product_type_source=product_type_source,
                    taxonomy=classification_taxonomy,
                )
            ),
        )
    )


def append_fx_rate_if_missing(
    *,
    client: httpx.Client,
    simulate_request: ProposalSimulateRequest,
    instrument_currency: str,
    portfolio_base_currency: str,
    base_url: str,
    as_of: str,
) -> None:
    if instrument_currency == portfolio_base_currency or has_fx_pair(
        fx_rates=simulate_request.market_data_snapshot.fx_rates,
        from_currency=instrument_currency,
        to_currency=portfolio_base_currency,
    ):
        return

    fx_payload = fetch_json_with_cache(
        client,
        cache=FX_LOOKUP_CACHE,
        cache_key=f"fx:{instrument_currency}:{portfolio_base_currency}",
        method="GET",
        base_url=base_url,
        path=FX_RATES_PATH.format(
            from_currency=instrument_currency,
            to_currency=portfolio_base_currency,
        ),
        error_code="LOTUS_CORE_STATEFUL_FX_LOOKUP_UNAVAILABLE",
    )
    latest_fx_row = select_latest_fx_row(fx_payload=fx_payload, as_of=as_of)
    if latest_fx_row is None:
        return

    fx_rate = decimal_or_none(latest_fx_row.get("rate"))
    if fx_rate is None:
        return
    simulate_request.market_data_snapshot.fx_rates.append(
        FxRate(pair=f"{instrument_currency}/{portfolio_base_currency}", rate=fx_rate)
    )


def enrich_stateful_simulate_request_for_trade_drafts(
    *,
    simulate_request: ProposalSimulateRequest,
    as_of: str,
    base_url: str,
    control_plane_base_url: str,
    timeout: httpx.Timeout,
    client_factory: HttpClientFactory,
) -> ProposalSimulateRequest:
    existing_priced_instruments = {
        price.instrument_id for price in simulate_request.market_data_snapshot.prices
    }
    existing_shelf_instruments = {entry.instrument_id for entry in simulate_request.shelf_entries}
    missing_instrument_ids = {
        trade.instrument_id
        for trade in simulate_request.proposed_trades
        if trade.instrument_id not in existing_priced_instruments
        or trade.instrument_id not in existing_shelf_instruments
    }
    if not missing_instrument_ids:
        return simulate_request

    enriched_request = cast(ProposalSimulateRequest, simulate_request.model_copy(deep=True))
    with client_factory(timeout) as client:
        enrichment_by_instrument_id = fetch_instrument_enrichment_bulk(
            client,
            base_url=control_plane_base_url,
            security_ids=sorted(missing_instrument_ids),
        )
        classification_taxonomy = fetch_classification_taxonomy(
            client,
            base_url=control_plane_base_url,
            as_of=as_of,
        )
        for instrument_id in sorted(missing_instrument_ids):
            instrument_payload = fetch_json_with_cache(
                client,
                cache=INSTRUMENT_LOOKUP_CACHE,
                cache_key=f"instrument:{instrument_id}",
                method="GET",
                base_url=base_url,
                path=INSTRUMENTS_PATH.format(instrument_id=instrument_id),
                error_code="LOTUS_CORE_STATEFUL_INSTRUMENT_LOOKUP_UNAVAILABLE",
            )
            instrument_row = select_instrument_row(instrument_payload)
            if instrument_row is None:
                continue

            price_payload = fetch_json_with_cache(
                client,
                cache=PRICE_LOOKUP_CACHE,
                cache_key=f"price:{instrument_id}",
                method="GET",
                base_url=base_url,
                path=PRICES_PATH.format(instrument_id=instrument_id),
                error_code="LOTUS_CORE_STATEFUL_PRICE_LOOKUP_UNAVAILABLE",
            )
            latest_price_row = select_latest_price_row(price_payload=price_payload, as_of=as_of)
            if latest_price_row is None:
                continue

            instrument_currency = str(
                instrument_row.get("currency") or latest_price_row.get("currency") or ""
            ).strip()
            if not instrument_currency:
                continue

            append_price_if_missing(
                simulate_request=enriched_request,
                instrument_id=instrument_id,
                instrument_currency=instrument_currency,
                latest_price_row=latest_price_row,
            )
            append_shelf_entry_if_missing(
                simulate_request=enriched_request,
                instrument_id=instrument_id,
                instrument_row=instrument_row,
                enrichment_row=enrichment_by_instrument_id.get(instrument_id),
                classification_taxonomy=classification_taxonomy,
            )
            append_fx_rate_if_missing(
                client=client,
                simulate_request=enriched_request,
                instrument_currency=instrument_currency,
                portfolio_base_currency=enriched_request.portfolio_snapshot.base_currency,
                base_url=base_url,
                as_of=as_of,
            )

    return enriched_request
