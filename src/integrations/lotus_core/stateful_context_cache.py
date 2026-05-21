from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, cast

from src.core.workspace.models import WorkspaceStatefulInput
from src.integrations.lotus_core.context_resolution import LotusCoreResolvedAdvisoryContext
from src.integrations.lotus_core.runtime_config import (
    env_non_negative_float,
    env_positive_int,
)
from src.integrations.lotus_core.timed_cache import TimedCache, TimedCacheStats

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


def stateful_context_cache_ttl_seconds() -> float:
    return env_non_negative_float(
        "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS",
        default=_DEFAULT_STATEFUL_CONTEXT_CACHE_TTL_SECONDS,
    )


def stateful_context_cache_max_size() -> int:
    return int(
        env_positive_int(
            "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE",
            default=_DEFAULT_STATEFUL_CONTEXT_CACHE_MAX_SIZE,
        )
    )


def stateful_context_cache_key(stateful_input: WorkspaceStatefulInput) -> str:
    return "|".join(
        [
            stateful_input.portfolio_id,
            stateful_input.as_of,
            stateful_input.household_id or "",
            stateful_input.mandate_id or "",
            stateful_input.benchmark_id or "",
        ]
    )


def clone_resolved_context(
    resolved: LotusCoreResolvedAdvisoryContext,
) -> LotusCoreResolvedAdvisoryContext:
    return LotusCoreResolvedAdvisoryContext(
        simulate_request=resolved.simulate_request.model_copy(deep=True),
        resolved_context=resolved.resolved_context.model_copy(deep=True),
    )


def clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload)


STATEFUL_CONTEXT_CACHE = TimedCache[str, LotusCoreResolvedAdvisoryContext](
    clone_value=clone_resolved_context,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
)
INSTRUMENT_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=clone_payload,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
)
INSTRUMENT_ENRICHMENT_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=clone_payload,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
)
CLASSIFICATION_TAXONOMY_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=clone_payload,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
)
PRICE_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=clone_payload,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
)
FX_LOOKUP_CACHE = TimedCache[str, dict[str, Any]](
    clone_value=clone_payload,
    ttl_seconds=stateful_context_cache_ttl_seconds,
    max_size=stateful_context_cache_max_size,
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


def get_cached_resolved_context(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext | None:
    return STATEFUL_CONTEXT_CACHE.get(stateful_context_cache_key(stateful_input))


def cache_resolved_context(
    stateful_input: WorkspaceStatefulInput,
    resolved: LotusCoreResolvedAdvisoryContext,
) -> None:
    STATEFUL_CONTEXT_CACHE.set(stateful_context_cache_key(stateful_input), resolved)


def reset_stateful_context_cache() -> None:
    STATEFUL_CONTEXT_CACHE.clear()
    INSTRUMENT_LOOKUP_CACHE.clear()
    INSTRUMENT_ENRICHMENT_CACHE.clear()
    CLASSIFICATION_TAXONOMY_CACHE.clear()
    PRICE_LOOKUP_CACHE.clear()
    FX_LOOKUP_CACHE.clear()
    with _FETCH_STATS_LOCK:
        for key in _FETCH_STATS:
            _FETCH_STATS[key] = 0


def get_stateful_context_cache_stats() -> dict[str, TimedCacheStats]:
    return {
        "resolved_context": STATEFUL_CONTEXT_CACHE.stats(),
        "instrument_lookup": INSTRUMENT_LOOKUP_CACHE.stats(),
        "instrument_enrichment": INSTRUMENT_ENRICHMENT_CACHE.stats(),
        "classification_taxonomy": CLASSIFICATION_TAXONOMY_CACHE.stats(),
        "price_lookup": PRICE_LOOKUP_CACHE.stats(),
        "fx_lookup": FX_LOOKUP_CACHE.stats(),
    }


def get_stateful_context_fetch_stats() -> StatefulContextFetchStats:
    with _FETCH_STATS_LOCK:
        return StatefulContextFetchStats(
            portfolio_fetches=_FETCH_STATS["portfolio_fetches"],
            positions_fetches=_FETCH_STATS["positions_fetches"],
            cash_fetches=_FETCH_STATS["cash_fetches"],
            instrument_fetches=_FETCH_STATS["instrument_fetches"],
            price_fetches=_FETCH_STATS["price_fetches"],
            fx_fetches=_FETCH_STATS["fx_fetches"],
        )


def record_fetch_stat(name: str) -> None:
    with _FETCH_STATS_LOCK:
        _FETCH_STATS[name] += 1


def cache_payload(
    cache: TimedCache[str, dict[str, Any]],
    *,
    cache_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return cast(dict[str, Any], cache.set(cache_key, payload))


def get_cached_payload(
    cache: TimedCache[str, dict[str, Any]],
    *,
    cache_key: str,
) -> dict[str, Any] | None:
    return cast(dict[str, Any] | None, cache.get(cache_key))
