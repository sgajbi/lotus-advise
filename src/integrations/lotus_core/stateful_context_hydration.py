from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, cast

import httpx

from src.core.portfolio_models import FxRate, Price, ShelfEntry
from src.core.proposal_request_models import ProposalSimulateRequest
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


@dataclass(frozen=True)
class _TradeDraftHydrationContext:
    client: httpx.Client
    as_of: str
    base_url: str
    enrichment_by_instrument_id: dict[str, dict[str, Any]]
    classification_taxonomy: ClassificationTaxonomy


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
    if _shelf_entry_exists(simulate_request, instrument_id=instrument_id):
        return
    asset_class, asset_class_source = _resolved_shelf_label(
        instrument_row.get("asset_class"),
        dimension_name="asset_class",
        taxonomy=classification_taxonomy,
    )
    product_type, product_type_source = _resolved_shelf_label(
        instrument_row.get("product_type"),
        dimension_name="product_type",
        taxonomy=classification_taxonomy,
        preserve_raw_when_ungoverned=True,
    )
    enrichment = enrichment_row or {}
    simulate_request.shelf_entries.append(
        _trade_draft_shelf_entry(
            instrument_id=instrument_id,
            instrument_row=instrument_row,
            enrichment_row=enrichment,
            asset_class=asset_class,
            asset_class_source=asset_class_source,
            product_type=product_type,
            product_type_source=product_type_source,
            classification_taxonomy=classification_taxonomy,
        )
    )


def _shelf_entry_exists(
    simulate_request: ProposalSimulateRequest,
    *,
    instrument_id: str,
) -> bool:
    return any(entry.instrument_id == instrument_id for entry in simulate_request.shelf_entries)


def _resolved_shelf_label(
    value: Any,
    *,
    dimension_name: str,
    taxonomy: ClassificationTaxonomy | None,
    preserve_raw_when_ungoverned: bool = False,
) -> tuple[str, str]:
    return cast(
        tuple[str, str],
        resolve_taxonomy_label(
            value,
            dimension_name=dimension_name,
            taxonomy=taxonomy,
            preserve_raw_when_ungoverned=preserve_raw_when_ungoverned,
        ),
    )


def _trade_draft_shelf_entry(
    *,
    instrument_id: str,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any],
    asset_class: str,
    asset_class_source: str,
    product_type: str,
    product_type_source: str,
    classification_taxonomy: ClassificationTaxonomy | None,
) -> ShelfEntry:
    return ShelfEntry(
        instrument_id=instrument_id,
        status="APPROVED",
        asset_class=asset_class,
        issuer_id=_source_or_enrichment_text(
            instrument_row=instrument_row,
            enrichment_row=enrichment_row,
            key="issuer_id",
        ),
        liquidity_tier=_trade_draft_liquidity_tier(
            instrument_row=instrument_row,
            enrichment_row=enrichment_row,
            asset_class=asset_class,
            product_type=product_type,
        ),
        attributes=_trade_draft_shelf_attributes(
            instrument_row=instrument_row,
            enrichment_row=enrichment_row,
            product_type=product_type,
            asset_class_source=asset_class_source,
            product_type_source=product_type_source,
            classification_taxonomy=classification_taxonomy,
        ),
    )


def _source_or_enrichment_text(
    *,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any],
    key: str,
) -> str | None:
    value = instrument_row.get(key)
    if value is None:
        value = enrichment_row.get(key)
    return cast(str | None, normalized_optional_str(value))


def _trade_draft_liquidity_tier(
    *,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any],
    asset_class: str,
    product_type: str,
) -> str | None:
    return cast(
        str | None,
        prefer_upstream_liquidity_tier(
            raw_liquidity_tier=instrument_row.get("liquidity_tier"),
            enrichment_liquidity_tier=enrichment_row.get("liquidity_tier"),
            asset_class=asset_class,
            product_type=product_type,
            sector=instrument_row.get("sector"),
            rating=instrument_row.get("rating"),
        ),
    )


def _trade_draft_shelf_attributes(
    *,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any],
    product_type: str,
    asset_class_source: str,
    product_type_source: str,
    classification_taxonomy: ClassificationTaxonomy | None,
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        shelf_attributes_from_payload(
            sector=instrument_row.get("sector"),
            country=instrument_row.get("country_of_risk"),
            product_type=product_type,
            rating=instrument_row.get("rating"),
            ultimate_parent_issuer_id=_source_or_enrichment_text(
                instrument_row=instrument_row,
                enrichment_row=enrichment_row,
                key="ultimate_parent_issuer_id",
            ),
            ultimate_parent_issuer_name=_source_or_enrichment_text(
                instrument_row=instrument_row,
                enrichment_row=enrichment_row,
                key="ultimate_parent_issuer_name",
            ),
        )
        | classification_supportability_attributes(
            asset_class_source=asset_class_source,
            product_type_source=product_type_source,
            taxonomy=classification_taxonomy,
        ),
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
    missing_instrument_ids = _missing_trade_instrument_ids(simulate_request)
    if not missing_instrument_ids:
        return simulate_request

    enriched_request = cast(ProposalSimulateRequest, simulate_request.model_copy(deep=True))
    with client_factory(timeout) as client:
        hydration_context = _build_trade_draft_hydration_context(
            client=client,
            as_of=as_of,
            base_url=base_url,
            control_plane_base_url=control_plane_base_url,
            missing_instrument_ids=missing_instrument_ids,
        )
        for instrument_id in sorted(missing_instrument_ids):
            _enrich_missing_trade_instrument(
                hydration_context,
                simulate_request=enriched_request,
                instrument_id=instrument_id,
            )

    return enriched_request


def _missing_trade_instrument_ids(
    simulate_request: ProposalSimulateRequest,
) -> set[str]:
    existing_priced_instruments = {
        price.instrument_id for price in simulate_request.market_data_snapshot.prices
    }
    existing_shelf_instruments = {entry.instrument_id for entry in simulate_request.shelf_entries}
    return {
        trade.instrument_id
        for trade in simulate_request.proposed_trades
        if trade.instrument_id not in existing_priced_instruments
        or trade.instrument_id not in existing_shelf_instruments
    }


def _build_trade_draft_hydration_context(
    *,
    client: httpx.Client,
    as_of: str,
    base_url: str,
    control_plane_base_url: str,
    missing_instrument_ids: set[str],
) -> _TradeDraftHydrationContext:
    return _TradeDraftHydrationContext(
        client=client,
        as_of=as_of,
        base_url=base_url,
        enrichment_by_instrument_id=fetch_instrument_enrichment_bulk(
            client,
            base_url=control_plane_base_url,
            security_ids=sorted(missing_instrument_ids),
        ),
        classification_taxonomy=fetch_classification_taxonomy(
            client,
            base_url=control_plane_base_url,
            as_of=as_of,
        ),
    )


def _enrich_missing_trade_instrument(
    hydration_context: _TradeDraftHydrationContext,
    *,
    simulate_request: ProposalSimulateRequest,
    instrument_id: str,
) -> None:
    instrument_row = _fetch_trade_instrument_row(hydration_context, instrument_id)
    if instrument_row is None:
        return
    latest_price_row = _fetch_trade_price_row(hydration_context, instrument_id)
    if latest_price_row is None:
        return
    instrument_currency = _trade_instrument_currency(instrument_row, latest_price_row)
    if not instrument_currency:
        return
    append_price_if_missing(
        simulate_request=simulate_request,
        instrument_id=instrument_id,
        instrument_currency=instrument_currency,
        latest_price_row=latest_price_row,
    )
    append_shelf_entry_if_missing(
        simulate_request=simulate_request,
        instrument_id=instrument_id,
        instrument_row=instrument_row,
        enrichment_row=hydration_context.enrichment_by_instrument_id.get(instrument_id),
        classification_taxonomy=hydration_context.classification_taxonomy,
    )
    append_fx_rate_if_missing(
        client=hydration_context.client,
        simulate_request=simulate_request,
        instrument_currency=instrument_currency,
        portfolio_base_currency=simulate_request.portfolio_snapshot.base_currency,
        base_url=hydration_context.base_url,
        as_of=hydration_context.as_of,
    )


def _fetch_trade_instrument_row(
    hydration_context: _TradeDraftHydrationContext,
    instrument_id: str,
) -> dict[str, Any] | None:
    instrument_payload = fetch_json_with_cache(
        hydration_context.client,
        cache=INSTRUMENT_LOOKUP_CACHE,
        cache_key=f"instrument:{instrument_id}",
        method="GET",
        base_url=hydration_context.base_url,
        path=INSTRUMENTS_PATH.format(instrument_id=instrument_id),
        error_code="LOTUS_CORE_STATEFUL_INSTRUMENT_LOOKUP_UNAVAILABLE",
    )
    return select_instrument_row(instrument_payload)


def _fetch_trade_price_row(
    hydration_context: _TradeDraftHydrationContext,
    instrument_id: str,
) -> dict[str, Any] | None:
    price_payload = fetch_json_with_cache(
        hydration_context.client,
        cache=PRICE_LOOKUP_CACHE,
        cache_key=f"price:{instrument_id}",
        method="GET",
        base_url=hydration_context.base_url,
        path=PRICES_PATH.format(instrument_id=instrument_id),
        error_code="LOTUS_CORE_STATEFUL_PRICE_LOOKUP_UNAVAILABLE",
    )
    return select_latest_price_row(price_payload=price_payload, as_of=hydration_context.as_of)


def _trade_instrument_currency(
    instrument_row: dict[str, Any],
    latest_price_row: dict[str, Any],
) -> str:
    return str(instrument_row.get("currency") or latest_price_row.get("currency") or "").strip()
