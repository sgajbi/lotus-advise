from __future__ import annotations

import os

import httpx


class RuntimeConfigurationError(ValueError):
    """Raised when an explicitly configured runtime setting is invalid."""


def _env_float(
    name: str,
    *,
    default: float,
    minimum: float,
    maximum: float | None = None,
) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except ValueError as exc:
        raise RuntimeConfigurationError(f"{name} must be a number") from exc
    if parsed < minimum:
        raise RuntimeConfigurationError(f"{name} must be greater than or equal to {minimum}")
    if maximum is not None and parsed > maximum:
        raise RuntimeConfigurationError(f"{name} must be less than or equal to {maximum}")
    return parsed


def env_non_negative_float(
    name: str,
    *,
    default: float,
    maximum: float | None = None,
) -> float:
    return _env_float(name, default=default, minimum=0.0, maximum=maximum)


def env_positive_float(
    name: str,
    *,
    default: float,
    maximum: float | None = None,
) -> float:
    return _env_float(name, default=default, minimum=0.001, maximum=maximum)


def env_positive_int(
    name: str,
    *,
    default: int,
    maximum: int | None = None,
) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise RuntimeConfigurationError(f"{name} must be an integer") from exc
    if parsed < 1:
        raise RuntimeConfigurationError(f"{name} must be greater than or equal to 1")
    if maximum is not None and parsed > maximum:
        raise RuntimeConfigurationError(f"{name} must be less than or equal to {maximum}")
    return parsed


def resolve_lotus_core_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_CORE_TIMEOUT_SECONDS", default=10.0))


def validate_configured_integration_runtime_settings() -> None:
    """Validate explicitly configured numeric integration settings before serving traffic."""

    env_positive_float("LOTUS_CORE_TIMEOUT_SECONDS", default=10.0)
    env_non_negative_float("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_TTL_SECONDS", default=15.0)
    env_positive_int("LOTUS_CORE_STATEFUL_CONTEXT_CACHE_MAX_SIZE", default=128)
    env_positive_float("LOTUS_AI_TIMEOUT_SECONDS", default=10.0)
    env_positive_float("LOTUS_RISK_TIMEOUT_SECONDS", default=10.0)
    env_positive_int("LOTUS_RISK_RETRY_ATTEMPTS", default=2, maximum=5)
    env_positive_float("LOTUS_RISK_RETRY_BACKOFF_SECONDS", default=0.1, maximum=2.0)
    env_positive_float("LOTUS_REPORT_TIMEOUT_SECONDS", default=30.0)
    env_positive_int("LOTUS_REPORT_STATUS_POLL_ATTEMPTS", default=3, maximum=5)
    env_non_negative_float("LOTUS_REPORT_STATUS_POLL_BACKOFF_SECONDS", default=0.0)
