import pytest

from src.integrations.lotus_core.runtime_config import (
    RuntimeConfigurationError,
    env_non_negative_float,
    env_positive_float,
    env_positive_int,
    resolve_lotus_core_timeout,
    validate_configured_integration_runtime_settings,
)


def test_runtime_config_uses_defaults_for_missing_values(monkeypatch) -> None:
    monkeypatch.delenv("LOTUS_CORE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", raising=False)
    monkeypatch.delenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", raising=False)

    timeout = resolve_lotus_core_timeout()

    assert timeout.connect == 10.0
    assert (
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
        == 15.0
    )
    assert env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128) == 128


def test_runtime_config_rejects_invalid_values_without_echoing_raw_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "secret-invalid-value")
    monkeypatch.setenv(
        "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS",
        "secret-invalid-value",
    )
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "secret-invalid-value")

    with pytest.raises(RuntimeConfigurationError) as timeout_error:
        resolve_lotus_core_timeout()
    with pytest.raises(RuntimeConfigurationError) as ttl_error:
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
    with pytest.raises(RuntimeConfigurationError) as size_error:
        env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128)

    error_text = "\n".join(str(error.value) for error in (timeout_error, ttl_error, size_error))
    assert "LOTUS_CORE_TIMEOUT_SECONDS" in error_text
    assert "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS" in error_text
    assert "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE" in error_text
    assert "secret-invalid-value" not in error_text


def test_runtime_config_rejects_out_of_range_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "0")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "-1")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "0")

    with pytest.raises(RuntimeConfigurationError):
        resolve_lotus_core_timeout()
    with pytest.raises(RuntimeConfigurationError):
        env_positive_float("LOTUS_CORE_TIMEOUT_SECONDS", default=10.0)
    with pytest.raises(RuntimeConfigurationError):
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
    with pytest.raises(RuntimeConfigurationError):
        env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128)


def test_runtime_config_rejects_values_above_explicit_maximum(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_RISK_RETRY_ATTEMPTS", "6")
    monkeypatch.setenv("LOTUS_RISK_RETRY_BACKOFF_SECONDS", "2.1")

    with pytest.raises(RuntimeConfigurationError):
        env_positive_int("LOTUS_RISK_RETRY_ATTEMPTS", default=2, maximum=5)
    with pytest.raises(RuntimeConfigurationError):
        env_positive_float("LOTUS_RISK_RETRY_BACKOFF_SECONDS", default=0.1, maximum=2.0)


@pytest.mark.parametrize(
    ("env_name", "configured_value"),
    [
        ("LOTUS_CORE_TIMEOUT_SECONDS", "invalid"),
        ("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "-1"),
        ("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "0"),
        ("LOTUS_AI_TIMEOUT_SECONDS", "0"),
        ("LOTUS_AI_ADVISORY_COPILOT_RETRY_ATTEMPTS", "4"),
        ("LOTUS_AI_ADVISORY_COPILOT_RETRY_BACKOFF_MS", "2001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_INPUT_CHARACTERS", "128001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_OUTPUT_CHARACTERS", "80001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_PROMPT_TOKENS", "32001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_COMPLETION_TOKENS", "8001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_TOTAL_TOKENS", "40001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_CHARGEABLE_COST_UNITS", "5000001"),
        ("LOTUS_AI_ADVISORY_COPILOT_MAX_CONCURRENT_REQUESTS", "17"),
        ("LOTUS_RISK_TIMEOUT_SECONDS", "invalid"),
        ("LOTUS_RISK_RETRY_ATTEMPTS", "6"),
        ("LOTUS_RISK_RETRY_BACKOFF_SECONDS", "2.1"),
        ("LOTUS_REPORT_TIMEOUT_SECONDS", "invalid"),
        ("LOTUS_REPORT_STATUS_POLL_ATTEMPTS", "6"),
        ("LOTUS_REPORT_STATUS_POLL_BACKOFF_SECONDS", "-0.1"),
    ],
)
def test_integration_runtime_settings_validator_rejects_invalid_configured_values(
    monkeypatch,
    env_name: str,
    configured_value: str,
) -> None:
    monkeypatch.setenv(env_name, configured_value)

    with pytest.raises(RuntimeConfigurationError, match=env_name):
        validate_configured_integration_runtime_settings()


def test_integration_runtime_settings_validator_accepts_missing_values(monkeypatch) -> None:
    for env_name in (
        "LOTUS_CORE_TIMEOUT_SECONDS",
        "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS",
        "LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE",
        "LOTUS_AI_TIMEOUT_SECONDS",
        "LOTUS_AI_ADVISORY_COPILOT_RETRY_ATTEMPTS",
        "LOTUS_AI_ADVISORY_COPILOT_RETRY_BACKOFF_MS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_INPUT_CHARACTERS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_OUTPUT_CHARACTERS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_PROMPT_TOKENS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_COMPLETION_TOKENS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_TOTAL_TOKENS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_CHARGEABLE_COST_UNITS",
        "LOTUS_AI_ADVISORY_COPILOT_MAX_CONCURRENT_REQUESTS",
        "LOTUS_RISK_TIMEOUT_SECONDS",
        "LOTUS_RISK_RETRY_ATTEMPTS",
        "LOTUS_RISK_RETRY_BACKOFF_SECONDS",
        "LOTUS_REPORT_TIMEOUT_SECONDS",
        "LOTUS_REPORT_STATUS_POLL_ATTEMPTS",
        "LOTUS_REPORT_STATUS_POLL_BACKOFF_SECONDS",
    ):
        monkeypatch.delenv(env_name, raising=False)

    validate_configured_integration_runtime_settings()


def test_runtime_config_accepts_valid_values(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_CORE_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", "0")
    monkeypatch.setenv("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", "16")

    timeout = resolve_lotus_core_timeout()

    assert timeout.connect == 2.5
    assert (
        env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0) == 0.0
    )
    assert env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128) == 16
