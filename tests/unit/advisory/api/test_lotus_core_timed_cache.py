from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from src.integrations.lotus_core.timed_cache import TimedCache


def test_timed_cache_returns_copy_safe_values() -> None:
    cache = TimedCache[str, dict[str, str]](
        clone_value=lambda value: dict(value),
        ttl_seconds=lambda: 15.0,
        max_size=lambda: 8,
    )

    first = cache.set("k1", {"value": "original"})
    first["value"] = "mutated"

    second = cache.get("k1")

    assert second == {"value": "original"}


def test_timed_cache_evicts_oldest_entry() -> None:
    cache = TimedCache[str, dict[str, str]](
        clone_value=lambda value: dict(value),
        ttl_seconds=lambda: 15.0,
        max_size=lambda: 1,
    )

    cache.set("k1", {"value": "one"})
    cache.set("k2", {"value": "two"})

    assert cache.get("k1") is None
    assert cache.get("k2") == {"value": "two"}
    stats = cache.stats()
    assert stats.evictions == 1
    assert stats.size == 1


def test_timed_cache_is_safe_under_parallel_get_set() -> None:
    cache = TimedCache[str, dict[str, str]](
        clone_value=lambda value: dict(value),
        ttl_seconds=lambda: 15.0,
        max_size=lambda: 16,
    )

    def _work(index: int) -> str | None:
        key = f"k{index % 3}"
        cache.set(key, {"value": str(index)})
        loaded = cache.get(key)
        return None if loaded is None else loaded["value"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_work, range(48)))

    assert all(result is not None for result in results)


def test_timed_cache_tracks_hits_misses_and_expirations() -> None:
    ttl_state = {"value": 15.0}
    cache = TimedCache[str, dict[str, str]](
        clone_value=lambda value: dict(value),
        ttl_seconds=lambda: ttl_state["value"],
        max_size=lambda: 8,
    )

    assert cache.get("missing") is None
    cache.set("k1", {"value": "one"})
    assert cache.get("k1") == {"value": "one"}
    ttl_state["value"] = 0.0
    cache.set("k2", {"value": "two"})
    assert cache.get("k2") is None

    stats = cache.stats()
    assert stats.hits == 1
    assert stats.misses == 2
    assert stats.expirations == 1
    assert stats.writes == 2
