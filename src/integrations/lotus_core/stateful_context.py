from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

import httpx

from src.core.models import (
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    PortfolioSnapshot,
    Price,
    ProposalSimulateRequest,
    ShelfEntry,
    ValuationMode,
)
from src.core.workspace.models import WorkspaceResolvedContext, WorkspaceStatefulInput
from src.integrations.lotus_core.classification import (
    ClassificationTaxonomy,
)
from src.integrations.lotus_core.classification import (
    classification_supportability_attributes as _classification_supportability_attributes,
)
from src.integrations.lotus_core.classification import (
    normalized_optional_str as _normalized_optional_str,
)
from src.integrations.lotus_core.classification import (
    prefer_upstream_liquidity_tier as _prefer_upstream_liquidity_tier,
)
from src.integrations.lotus_core.classification import (
    resolve_taxonomy_label as _resolve_taxonomy_label,
)
from src.integrations.lotus_core.context_resolution import (
    LotusCoreResolvedAdvisoryContext,
)
from src.integrations.lotus_core.runtime_config import (
    resolve_lotus_core_timeout,
)
from src.integrations.lotus_core.stateful_context_cache import (
    FX_LOOKUP_CACHE as _FX_LOOKUP_CACHE,
)
from src.integrations.lotus_core.stateful_context_cache import (
    INSTRUMENT_LOOKUP_CACHE as _INSTRUMENT_LOOKUP_CACHE,
)
from src.integrations.lotus_core.stateful_context_cache import (
    PRICE_LOOKUP_CACHE as _PRICE_LOOKUP_CACHE,
)
from src.integrations.lotus_core.stateful_context_cache import (
    StatefulContextFetchStats,
    stateful_context_cache_max_size,
    stateful_context_cache_ttl_seconds,
)
from src.integrations.lotus_core.stateful_context_cache import (
    cache_resolved_context as _cache_resolved_context,
)
from src.integrations.lotus_core.stateful_context_cache import (
    clone_resolved_context as _clone_resolved_context,
)
from src.integrations.lotus_core.stateful_context_cache import (
    get_cached_resolved_context as _get_cached_resolved_context,
)
from src.integrations.lotus_core.stateful_context_cache import (
    get_stateful_context_cache_stats as _get_stateful_context_cache_stats,
)
from src.integrations.lotus_core.stateful_context_cache import (
    get_stateful_context_fetch_stats as _get_stateful_context_fetch_stats,
)
from src.integrations.lotus_core.stateful_context_cache import (
    reset_stateful_context_cache as _reset_stateful_context_cache,
)
from src.integrations.lotus_core.stateful_context_routes import (
    FX_RATES_PATH as _FX_RATES_PATH,
)
from src.integrations.lotus_core.stateful_context_routes import (
    INSTRUMENTS_PATH as _INSTRUMENTS_PATH,
)
from src.integrations.lotus_core.stateful_context_routes import (
    PORTFOLIO_PATH as _PORTFOLIO_PATH,
)
from src.integrations.lotus_core.stateful_context_routes import (
    PRICES_PATH as _PRICES_PATH,
)
from src.integrations.lotus_core.stateful_context_routes import (
    cash_balances_path,
    positions_path,
    resolve_control_plane_base_url,
    resolve_query_base_url,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    LotusCoreStatefulContextUnavailableError,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    fetch_classification_taxonomy as _fetch_classification_taxonomy,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    fetch_instrument_enrichment_bulk as _fetch_instrument_enrichment_bulk,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    fetch_json_with_cache as _fetch_json_with_cache,
)
from src.integrations.lotus_core.stateful_context_source_reads import (
    request_json as _request_json,
)
from src.integrations.lotus_core.stateful_context_translation import (
    build_cash_balances as _build_cash_balances,
)
from src.integrations.lotus_core.stateful_context_translation import (
    build_positions as _build_positions,
)
from src.integrations.lotus_core.stateful_context_translation import (
    build_prices as _build_prices,
)
from src.integrations.lotus_core.stateful_context_translation import (
    build_shelf_entries as _build_shelf_entries,
)
from src.integrations.lotus_core.stateful_context_translation import (
    decimal_or_none as _decimal_or_none,
)
from src.integrations.lotus_core.stateful_context_translation import (
    derive_fx_rates as _derive_fx_rates,
)
from src.integrations.lotus_core.stateful_context_translation import (
    shelf_attributes_from_payload as _shelf_attributes_from_payload,
)
from src.integrations.lotus_core.timed_cache import TimedCacheStats


def _resolve_timeout() -> httpx.Timeout:
    return resolve_lotus_core_timeout()


def _stateful_context_cache_ttl_seconds() -> float:
    return stateful_context_cache_ttl_seconds()


def _stateful_context_cache_max_size() -> int:
    return stateful_context_cache_max_size()


def reset_stateful_context_cache_for_tests() -> None:
    _reset_stateful_context_cache()


def get_stateful_context_cache_stats_for_tests() -> dict[str, TimedCacheStats]:
    return _get_stateful_context_cache_stats()


def get_stateful_context_fetch_stats_for_tests() -> StatefulContextFetchStats:
    return _get_stateful_context_fetch_stats()


def _resolve_query_base_url() -> str:
    try:
        return resolve_query_base_url()
    except ValueError as exc:
        raise LotusCoreStatefulContextUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"
        ) from exc


def _positions_path(*, portfolio_id: str, as_of: str) -> str:
    return positions_path(portfolio_id=portfolio_id, as_of=as_of)


def _cash_balances_path(*, portfolio_id: str, as_of: str) -> str:
    return cash_balances_path(portfolio_id=portfolio_id, as_of=as_of)


def _resolve_control_plane_base_url() -> str:
    try:
        return resolve_control_plane_base_url()
    except ValueError as exc:
        raise LotusCoreStatefulContextUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"
        ) from exc


def _require_decimal(value: Any, *, error_code: str) -> Decimal:
    parsed = _decimal_or_none(value)
    if parsed is None:
        raise LotusCoreStatefulContextUnavailableError(error_code)
    return parsed


def _select_latest_dated_row(
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


def _has_fx_pair(
    *,
    fx_rates: list[FxRate],
    from_currency: str,
    to_currency: str,
) -> bool:
    direct_pair = f"{from_currency}/{to_currency}"
    inverse_pair = f"{to_currency}/{from_currency}"
    return any(rate.pair in {direct_pair, inverse_pair} for rate in fx_rates)


def _select_instrument_row(instrument_payload: dict[str, Any]) -> dict[str, Any] | None:
    instrument_rows = instrument_payload.get("instruments")
    if not isinstance(instrument_rows, list) or not instrument_rows:
        return None
    instrument_row = instrument_rows[0]
    return instrument_row if isinstance(instrument_row, dict) else None


def _select_latest_price_row(
    *,
    price_payload: dict[str, Any],
    as_of: str,
) -> dict[str, Any] | None:
    price_rows = price_payload.get("prices")
    if not isinstance(price_rows, list):
        return None
    return _select_latest_dated_row(price_rows, date_key="price_date", as_of=as_of)


def _select_latest_fx_row(
    *,
    fx_payload: dict[str, Any],
    as_of: str,
) -> dict[str, Any] | None:
    fx_rows = fx_payload.get("rates")
    if not isinstance(fx_rows, list):
        return None
    return _select_latest_dated_row(fx_rows, date_key="rate_date", as_of=as_of)


def _append_price_if_missing(
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
    price_value = _decimal_or_none(latest_price_row.get("price"))
    if price_value is None:
        return
    simulate_request.market_data_snapshot.prices.append(
        Price(
            instrument_id=instrument_id,
            price=price_value,
            currency=instrument_currency,
        )
    )


def _append_shelf_entry_if_missing(
    *,
    simulate_request: ProposalSimulateRequest,
    instrument_id: str,
    instrument_row: dict[str, Any],
    enrichment_row: dict[str, Any] | None = None,
    classification_taxonomy: ClassificationTaxonomy | None = None,
) -> None:
    if any(entry.instrument_id == instrument_id for entry in simulate_request.shelf_entries):
        return
    asset_class, asset_class_source = _resolve_taxonomy_label(
        instrument_row.get("asset_class"),
        dimension_name="asset_class",
        taxonomy=classification_taxonomy,
    )
    product_type, product_type_source = _resolve_taxonomy_label(
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
            issuer_id=_normalized_optional_str(
                instrument_row.get("issuer_id")
                if instrument_row.get("issuer_id") is not None
                else (enrichment_row or {}).get("issuer_id")
            ),
            liquidity_tier=_prefer_upstream_liquidity_tier(
                raw_liquidity_tier=instrument_row.get("liquidity_tier"),
                enrichment_liquidity_tier=(enrichment_row or {}).get("liquidity_tier"),
                asset_class=asset_class,
                product_type=product_type,
                sector=instrument_row.get("sector"),
                rating=instrument_row.get("rating"),
            ),
            attributes=(
                _shelf_attributes_from_payload(
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
                | _classification_supportability_attributes(
                    asset_class_source=asset_class_source,
                    product_type_source=product_type_source,
                    taxonomy=classification_taxonomy,
                )
            ),
        )
    )


def _append_fx_rate_if_missing(
    *,
    client: httpx.Client,
    simulate_request: ProposalSimulateRequest,
    instrument_currency: str,
    portfolio_base_currency: str,
    base_url: str,
    as_of: str,
) -> None:
    if instrument_currency == portfolio_base_currency or _has_fx_pair(
        fx_rates=simulate_request.market_data_snapshot.fx_rates,
        from_currency=instrument_currency,
        to_currency=portfolio_base_currency,
    ):
        return

    fx_payload = _fetch_json_with_cache(
        client,
        cache=_FX_LOOKUP_CACHE,
        cache_key=f"fx:{instrument_currency}:{portfolio_base_currency}",
        method="GET",
        base_url=base_url,
        path=_FX_RATES_PATH.format(
            from_currency=instrument_currency,
            to_currency=portfolio_base_currency,
        ),
        error_code="LOTUS_CORE_STATEFUL_FX_LOOKUP_UNAVAILABLE",
    )
    latest_fx_row = _select_latest_fx_row(fx_payload=fx_payload, as_of=as_of)
    if latest_fx_row is None:
        return

    fx_rate = _decimal_or_none(latest_fx_row.get("rate"))
    if fx_rate is None:
        return
    simulate_request.market_data_snapshot.fx_rates.append(
        FxRate(pair=f"{instrument_currency}/{portfolio_base_currency}", rate=fx_rate)
    )


def enrich_stateful_simulate_request_for_trade_drafts(
    *,
    simulate_request: ProposalSimulateRequest,
    as_of: str,
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

    base_url = _resolve_query_base_url()
    control_plane_base_url = _resolve_control_plane_base_url()
    enriched_request = cast(ProposalSimulateRequest, simulate_request.model_copy(deep=True))
    with httpx.Client(timeout=_resolve_timeout()) as client:
        enrichment_by_instrument_id = _fetch_instrument_enrichment_bulk(
            client,
            base_url=control_plane_base_url,
            security_ids=sorted(missing_instrument_ids),
        )
        classification_taxonomy = _fetch_classification_taxonomy(
            client,
            base_url=control_plane_base_url,
            as_of=as_of,
        )
        for instrument_id in sorted(missing_instrument_ids):
            instrument_payload = _fetch_json_with_cache(
                client,
                cache=_INSTRUMENT_LOOKUP_CACHE,
                cache_key=f"instrument:{instrument_id}",
                method="GET",
                base_url=base_url,
                path=_INSTRUMENTS_PATH.format(instrument_id=instrument_id),
                error_code="LOTUS_CORE_STATEFUL_INSTRUMENT_LOOKUP_UNAVAILABLE",
            )
            instrument_row = _select_instrument_row(instrument_payload)
            if instrument_row is None:
                continue

            price_payload = _fetch_json_with_cache(
                client,
                cache=_PRICE_LOOKUP_CACHE,
                cache_key=f"price:{instrument_id}",
                method="GET",
                base_url=base_url,
                path=_PRICES_PATH.format(instrument_id=instrument_id),
                error_code="LOTUS_CORE_STATEFUL_PRICE_LOOKUP_UNAVAILABLE",
            )
            latest_price_row = _select_latest_price_row(price_payload=price_payload, as_of=as_of)
            if latest_price_row is None:
                continue

            instrument_currency = str(
                instrument_row.get("currency") or latest_price_row.get("currency") or ""
            ).strip()
            if not instrument_currency:
                continue

            _append_price_if_missing(
                simulate_request=enriched_request,
                instrument_id=instrument_id,
                instrument_currency=instrument_currency,
                latest_price_row=latest_price_row,
            )
            _append_shelf_entry_if_missing(
                simulate_request=enriched_request,
                instrument_id=instrument_id,
                instrument_row=instrument_row,
                enrichment_row=enrichment_by_instrument_id.get(instrument_id),
                classification_taxonomy=classification_taxonomy,
            )
            _append_fx_rate_if_missing(
                client=client,
                simulate_request=enriched_request,
                instrument_currency=instrument_currency,
                portfolio_base_currency=enriched_request.portfolio_snapshot.base_currency,
                base_url=base_url,
                as_of=as_of,
            )

    return enriched_request


def resolve_stateful_context_with_lotus_core(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext:
    cached = _get_cached_resolved_context(stateful_input)
    if cached is not None:
        return cached

    base_url = _resolve_query_base_url()
    control_plane_base_url = _resolve_control_plane_base_url()
    with httpx.Client(timeout=_resolve_timeout()) as client:
        portfolio_payload = _request_json(
            client,
            method="GET",
            base_url=base_url,
            path=_PORTFOLIO_PATH.format(portfolio_id=stateful_input.portfolio_id),
            error_code="LOTUS_CORE_STATEFUL_PORTFOLIO_UNAVAILABLE",
        )
        positions_payload = _request_json(
            client,
            method="GET",
            base_url=base_url,
            path=_positions_path(
                portfolio_id=stateful_input.portfolio_id,
                as_of=stateful_input.as_of,
            ),
            error_code="LOTUS_CORE_STATEFUL_POSITIONS_UNAVAILABLE",
        )
        cash_payload = _request_json(
            client,
            method="GET",
            base_url=base_url,
            path=_cash_balances_path(
                portfolio_id=stateful_input.portfolio_id,
                as_of=stateful_input.as_of,
            ),
            error_code="LOTUS_CORE_STATEFUL_CASH_UNAVAILABLE",
        )
        held_instrument_ids = sorted(
            {
                str(raw_position.get("security_id") or "").strip()
                for raw_position in positions_payload.get("positions", [])
                if isinstance(raw_position, dict)
                and str(raw_position.get("asset_class") or "").strip().lower() != "cash"
                and str(raw_position.get("security_id") or "").strip()
            }
        )
        enrichment_by_instrument_id = _fetch_instrument_enrichment_bulk(
            client,
            base_url=control_plane_base_url,
            security_ids=held_instrument_ids,
        )
        classification_taxonomy = _fetch_classification_taxonomy(
            client,
            base_url=control_plane_base_url,
            as_of=stateful_input.as_of,
        )

    portfolio_id = str(portfolio_payload.get("portfolio_id") or stateful_input.portfolio_id).strip()
    base_currency = str(portfolio_payload.get("base_currency") or "").strip()
    if not portfolio_id or not base_currency:
        raise LotusCoreStatefulContextUnavailableError("LOTUS_CORE_STATEFUL_CONTEXT_INVALID")

    resolved_as_of = str(cash_payload.get("resolved_as_of_date") or stateful_input.as_of).strip()
    if not resolved_as_of:
        raise LotusCoreStatefulContextUnavailableError("LOTUS_CORE_STATEFUL_CONTEXT_INVALID")

    portfolio_snapshot_id = f"lotus-core:portfolio:{portfolio_id}:{resolved_as_of}"
    market_data_snapshot_id = f"lotus-core:market-data:{portfolio_id}:{resolved_as_of}"

    simulate_request = ProposalSimulateRequest(
        portfolio_snapshot=PortfolioSnapshot(
            snapshot_id=portfolio_snapshot_id,
            portfolio_id=portfolio_id,
            base_currency=base_currency,
            positions=_build_positions(
                positions_payload,
                portfolio_base_currency=base_currency,
            ),
            cash_balances=_build_cash_balances(cash_payload),
        ),
        market_data_snapshot=MarketDataSnapshot(
            snapshot_id=market_data_snapshot_id,
            prices=_build_prices(positions_payload),
            fx_rates=_derive_fx_rates(
                portfolio_base_currency=base_currency,
                positions_payload=positions_payload,
                cash_payload=cash_payload,
            ),
        ),
        shelf_entries=_build_shelf_entries(
            positions_payload=positions_payload,
            cash_payload=cash_payload,
            enrichment_by_instrument_id=enrichment_by_instrument_id,
            classification_taxonomy=classification_taxonomy,
        ),
        options=EngineOptions(
            enable_proposal_simulation=True,
            valuation_mode=ValuationMode.TRUST_SNAPSHOT,
        ),
        proposed_cash_flows=[],
        proposed_trades=[],
        reference_model=None,
    )
    resolved_context = WorkspaceResolvedContext(
        portfolio_id=portfolio_id,
        as_of=resolved_as_of,
        portfolio_snapshot_id=portfolio_snapshot_id,
        market_data_snapshot_id=market_data_snapshot_id,
    )
    resolved = LotusCoreResolvedAdvisoryContext(
        simulate_request=simulate_request,
        resolved_context=resolved_context,
    )
    _cache_resolved_context(stateful_input, resolved)
    return _clone_resolved_context(resolved)
