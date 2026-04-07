from __future__ import annotations

import os

import httpx


def _env_float(name: str, *, default: float, minimum: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return default
    return parsed


def env_non_negative_float(name: str, *, default: float) -> float:
    return _env_float(name, default=default, minimum=0.0)


def env_positive_float(name: str, *, default: float) -> float:
    return _env_float(name, default=default, minimum=0.001)


def env_positive_int(name: str, *, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return parsed


def resolve_lotus_core_timeout() -> httpx.Timeout:
    return httpx.Timeout(env_positive_float("LOTUS_CORE_TIMEOUT_SECONDS", default=10.0))
