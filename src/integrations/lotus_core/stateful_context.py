from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import RLock
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

import httpx

from src.core.models import (
    CashBalance,
    EngineOptions,
    FxRate,
    MarketDataSnapshot,
    PortfolioSnapshot,
    Position,
    Price,
    ProposalSimulateRequest,
    ShelfEntry,
)
from src.core.workspace.models import WorkspaceResolvedContext, WorkspaceStatefulInput
from src.integrations.lotus_core.context_resolution import (
    LotusCoreContextResolutionError,
    LotusCoreResolvedAdvisoryContext,
)
from src.integrations.lotus_core.runtime_config import (
    env_non_negative_float,
    env_positive_int,
    resolve_lotus_core_timeout,
)
from src.integrations.lotus_core.timed_cache import TimedCache, TimedCacheStats

_DEFAULT_LOTUS_CORE_QUERY_BASE_URL = "http://core-query.dev.lotus"
_PORTFOLIO_PATH = "/portfolios/{portfolio_id}"
_POSITIONS_PATH = "/portfolios/{portfolio_id}/positions"
_CASH_BALANCES_PATH = "/reporting/cash-balances/query"
_INSTRUMENTS_PATH = "/instruments/?security_id={instrument_id}"
_PRICES_PATH = "/prices/?security_id={instrument_id}"
_FX_RATES_PATH = "/fx-rates/?from_currency={from_currency}&to_currency={to_currency}"
_DEFAULT_STATEFUL_CONTEXT_CACHE_TTL_SECONDS = 15.0
_DEFAULT_STATEFUL_CONTEXT_CACHE_MAX_SIZE = 128


@dataclass(frozen=True)
class StatefulContextFetchStats:
    portfolio_fetches: int
    positions_fetches: int
    cash_fetches: int
    instrument_fetches: int
    price_fetches: int
    fx_fetches: int


class LotusCoreStatefulContextUnavailableError(LotusCoreContextResolutionError):
    pass


def _resolve_timeout() -> httpx.Timeout:
    return resolve_lotus_core_timeout()


def _stateful_context_cache_ttl_seconds() -> float:
    return float(
        env_non_negative_float(
            "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS",
            default=_DEFAULT_STATEFUL_CONTEXT_CACHE_TTL_SECONDS,
        )
    )


def _stateful_context_cache_max_size() -> int:
    return int(
        env_positive_int(
            "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE",
            default=_DEFAULT_STATEFUL_CONTEXT_CACHE_MAX_SIZE,
        )
    )


def _cache_key(stateful_input: WorkspaceStatefulInput) -> str:
    return "|".join(
        [
            stateful_input.portfolio_id,
            stateful_input.as_of,
            stateful_input.household_id or "",
            stateful_input.mandate_id or "",
            stateful_input.benchmark_id or "",
        ]
    )


def _clone_resolved_context(
    resolved: LotusCoreResolvedAdvisoryContext,
) -> LotusCoreResolvedAdvisoryContext:
    return LotusCoreResolvedAdvisoryContext(
        simulate_request=resolved.simulate_request.model_copy(deep=True),
        resolved_context=resolved.resolved_context.model_copy(deep=True),
    )


def _clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload)


def _shelf_attributes_from_payload(
    *,
    sector: Any = None,
    country: Any = None,
    product_type: Any = None,
    rating: Any = None,
) -> dict[str, str]:
    attributes = {"source": "LOTUS_CORE_STATEFUL_CONTEXT"}
    optional_values = {
        "sector": sector,
        "country": country,
        "product_type": product_type,
        "rating": rating,
    }
    for key, raw_value in optional_values.items():
        value = str(raw_value or "").strip()
        if value:
            attributes[key] = value
    return attributes


_STATEFUL_CONTEXT_CACHE = TimedCache[str, LotusCoreResolvedAdvisoryContext](
    clone_value=_clone_resolved_context,
    ttl_seconds=_stateful_context_cache_ttl_seconds,
    max_size=_stateful_context_cache_max_size,
)
_INSTRUMENT_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=_clone_payload,
    ttl_seconds=_stateful_context_cache_ttl_seconds,
    max_size=_stateful_context_cache_max_size,
)
_PRICE_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=_clone_payload,
    ttl_seconds=_stateful_context_cache_ttl_seconds,
    max_size=_stateful_context_cache_max_size,
)
_FX_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=_clone_payload,
    ttl_seconds=_stateful_context_cache_ttl_seconds,
    max_size=_stateful_context_cache_max_size,
)
_FETCH_STATS_LOCK = RLock()
_FETCH_STATS = {
    "portfolio_fetches": 0,
    "positions_fetches": 0,
    "cash_fetches": 0,
    "instrument_fetches": 0,
    "price_fetches": 0,
    "fx_fetches": 0,
}


def _get_cached_resolved_context(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext | None:
    return _STATEFUL_CONTEXT_CACHE.get(_cache_key(stateful_input))


def _cache_resolved_context(
    stateful_input: WorkspaceStatefulInput,
    resolved: LotusCoreResolvedAdvisoryContext,
) -> None:
    _STATEFUL_CONTEXT_CACHE.set(_cache_key(stateful_input), resolved)


def reset_stateful_context_cache_for_tests() -> None:
    _STATEFUL_CONTEXT_CACHE.clear()
    _INSTRUMENT_LOOKUP_CACHE.clear()
    _PRICE_LOOKUP_CACHE.clear()
    _FX_LOOKUP_CACHE.clear()
    with _FETCH_STATS_LOCK:
        for key in _FETCH_STATS:
            _FETCH_STATS[key] = 0


def get_stateful_context_cache_stats_for_tests() -> dict[str, TimedCacheStats]:
    return {
        "resolved_context": _STATEFUL_CONTEXT_CACHE.stats(),
        "instrument_lookup": _INSTRUMENT_LOOKUP_CACHE.stats(),
        "price_lookup": _PRICE_LOOKUP_CACHE.stats(),
        "fx_lookup": _FX_LOOKUP_CACHE.stats(),
    }


def get_stateful_context_fetch_stats_for_tests() -> StatefulContextFetchStats:
    with _FETCH_STATS_LOCK:
        return StatefulContextFetchStats(
            portfolio_fetches=_FETCH_STATS["portfolio_fetches"],
            positions_fetches=_FETCH_STATS["positions_fetches"],
            cash_fetches=_FETCH_STATS["cash_fetches"],
            instrument_fetches=_FETCH_STATS["instrument_fetches"],
            price_fetches=_FETCH_STATS["price_fetches"],
            fx_fetches=_FETCH_STATS["fx_fetches"],
        )


def _record_fetch_stat(name: str) -> None:
    with _FETCH_STATS_LOCK:
        _FETCH_STATS[name] += 1


def _cache_payload(
    cache: TimedCache[str, dict[str, Any]],
    *,
    cache_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return cast(dict[str, Any], cache.set(cache_key, payload))


def _get_cached_payload(
    cache: TimedCache[str, dict[str, Any]],
    *,
    cache_key: str,
) -> dict[str, Any] | None:
    return cast(dict[str, Any] | None, cache.get(cache_key))


def _resolve_query_base_url() -> str:
    explicit = os.getenv("LOTUS_CORE_QUERY_BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    configured = os.getenv("LOTUS_CORE_BASE_URL")
    if configured:
        split = urlsplit(configured)
        host = split.hostname
        if host is None:
            raise LotusCoreStatefulContextUnavailableError(
                "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"
            )
        port = split.port
        netloc = host
        if split.username or split.password:
            auth = split.username or ""
            if split.password:
                auth = f"{auth}:{split.password}"
            netloc = f"{auth}@{host}"
        if port is not None:
            query_port = 8201 if port == 8202 else port
            netloc = f"{netloc}:{query_port}"
        return urlunsplit((split.scheme or "http", netloc, split.path.rstrip("/"), "", ""))

    return _DEFAULT_LOTUS_CORE_QUERY_BASE_URL


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _require_decimal(value: Any, *, error_code: str) -> Decimal:
    parsed = _decimal_or_none(value)
    if parsed is None:
        raise LotusCoreStatefulContextUnavailableError(error_code)
    return parsed


def _request_json(
    client: httpx.Client,
    *,
    method: str,
    base_url: str,
    path: str,
    error_code: str,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if error_code == "LOTUS_CORE_STATEFUL_PORTFOLIO_UNAVAILABLE":
        _record_fetch_stat("portfolio_fetches")
    elif error_code == "LOTUS_CORE_STATEFUL_POSITIONS_UNAVAILABLE":
        _record_fetch_stat("positions_fetches")
    elif error_code == "LOTUS_CORE_STATEFUL_CASH_UNAVAILABLE":
        _record_fetch_stat("cash_fetches")
    elif error_code == "LOTUS_CORE_STATEFUL_INSTRUMENT_LOOKUP_UNAVAILABLE":
        _record_fetch_stat("instrument_fetches")
    elif error_code == "LOTUS_CORE_STATEFUL_PRICE_LOOKUP_UNAVAILABLE":
        _record_fetch_stat("price_fetches")
    elif error_code == "LOTUS_CORE_STATEFUL_FX_LOOKUP_UNAVAILABLE":
        _record_fetch_stat("fx_fetches")
    url = f"{base_url}{path}"
    try:
        response = client.request(method, url, json=json_body)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LotusCoreStatefulContextUnavailableError(error_code) from exc

    if not isinstance(payload, dict):
        raise LotusCoreStatefulContextUnavailableError(error_code)
    return payload


def _fetch_json_with_cache(
    client: httpx.Client,
    *,
    cache: TimedCache[str, dict[str, Any]],
    cache_key: str,
    method: str,
    base_url: str,
    path: str,
    error_code: str,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cached_payload = _get_cached_payload(cache, cache_key=cache_key)
    if cached_payload is not None:
        return cached_payload
    payload = _request_json(
        client,
        method=method,
        base_url=base_url,
        path=path,
        error_code=error_code,
        json_body=json_body,
    )
    return _cache_payload(cache, cache_key=cache_key, payload=payload)


def _build_cash_balances(cash_payload: dict[str, Any]) -> list[CashBalance]:
    balances: list[CashBalance] = []
    for account in cash_payload.get("cash_accounts", []):
        if not isinstance(account, dict):
            continue
        currency = str(account.get("account_currency") or "").strip()
        if not currency:
            continue
        amount = _decimal_or_none(account.get("balance_account_currency"))
        if amount is None:
            continue
        balances.append(CashBalance(currency=currency, amount=amount))
    return balances


def _build_positions(positions_payload: dict[str, Any]) -> list[Position]:
    positions: list[Position] = []
    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        asset_class = str(raw_position.get("asset_class") or "").strip().lower()
        if asset_class == "cash":
            continue
        instrument_id = str(raw_position.get("security_id") or "").strip()
        quantity = _decimal_or_none(raw_position.get("quantity"))
        if not instrument_id or quantity is None:
            continue
        positions.append(Position(instrument_id=instrument_id, quantity=quantity))
    return positions


def _build_prices(positions_payload: dict[str, Any]) -> list[Price]:
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
        price = _decimal_or_none(valuation.get("market_price"))
        if price is None:
            continue
        price_map[instrument_id] = Price(
            instrument_id=instrument_id,
            price=price,
            currency=currency,
        )
    return list(price_map.values())


def _derive_fx_rates(
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
        numerator_decimal = _decimal_or_none(numerator)
        denominator_decimal = _decimal_or_none(denominator)
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


def _build_shelf_entries(
    *,
    positions_payload: dict[str, Any],
    cash_payload: dict[str, Any],
) -> list[ShelfEntry]:
    shelf_by_instrument: dict[str, ShelfEntry] = {}

    for raw_position in positions_payload.get("positions", []):
        if not isinstance(raw_position, dict):
            continue
        instrument_id = str(raw_position.get("security_id") or "").strip()
        if not instrument_id:
            continue
        asset_class = str(raw_position.get("asset_class") or "UNKNOWN").strip().upper()
        shelf_by_instrument[instrument_id] = ShelfEntry(
            instrument_id=instrument_id,
            status="APPROVED",
            asset_class=asset_class or "UNKNOWN",
            attributes=_shelf_attributes_from_payload(
                sector=raw_position.get("sector"),
                country=raw_position.get("country_of_risk"),
                product_type=raw_position.get("product_type"),
                rating=raw_position.get("rating"),
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
            attributes=_shelf_attributes_from_payload(product_type="Cash"),
        )

    return list(shelf_by_instrument.values())


def _select_latest_dated_row(
    rows: list[dict[str, Any]],
    *,
    date_key: str,
    as_of: str,
) -> dict[str, Any] | None:
    dated_rows = [
        row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get(date_key), str)
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
) -> None:
    if any(entry.instrument_id == instrument_id for entry in simulate_request.shelf_entries):
        return
    asset_class = str(instrument_row.get("asset_class") or "UNKNOWN").strip().upper()
    simulate_request.shelf_entries.append(
        ShelfEntry(
            instrument_id=instrument_id,
            status="APPROVED",
            asset_class=asset_class or "UNKNOWN",
            attributes=_shelf_attributes_from_payload(
                sector=instrument_row.get("sector"),
                country=instrument_row.get("country_of_risk"),
                product_type=instrument_row.get("product_type"),
                rating=instrument_row.get("rating"),
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
    enriched_request = simulate_request.model_copy(deep=True)
    with httpx.Client(timeout=_resolve_timeout()) as client:
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
            path=_POSITIONS_PATH.format(portfolio_id=stateful_input.portfolio_id),
            error_code="LOTUS_CORE_STATEFUL_POSITIONS_UNAVAILABLE",
        )
        cash_payload = _request_json(
            client,
            method="POST",
            base_url=base_url,
            path=_CASH_BALANCES_PATH,
            error_code="LOTUS_CORE_STATEFUL_CASH_UNAVAILABLE",
            json_body={"portfolio_id": stateful_input.portfolio_id},
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
            positions=_build_positions(positions_payload),
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
        ),
        options=EngineOptions(enable_proposal_simulation=True),
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
