from src.integrations.lotus_core.runtime_config import (
    env_non_negative_float,
    env_positive_float,
    env_positive_int,
    resolve_lotus_core_timeout,
)


def test_runtime_config_uses_defaults_for_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "invalid")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "invalid")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "invalid")

    timeout = resolve_lotus_core_timeout()

    assert timeout.connect == 10.0
    assert (
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
        == 15.0
    )
    assert env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128) == 128


def test_runtime_config_rejects_out_of_range_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "-1")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "0")

    timeout = resolve_lotus_core_timeout()

    assert timeout.connect == 10.0
    assert env_positive_float("LOTUS_CORE_TIMEOUT_SECONDS", default=10.0) == 10.0
    assert (
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
        == 15.0
    )
    assert env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128) == 128


def test_runtime_config_accepts_valid_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "0")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "16")

    timeout = resolve_lotus_core_timeout()

    assert timeout.connect == 2.5
    assert (
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
        == 0.0
    )
    assert env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128) == 16
