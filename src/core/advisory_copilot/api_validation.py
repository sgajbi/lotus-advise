from __future__ import annotations

from typing import Any, cast

from src.core.common.actors import normalize_required_actor_id

COPILOT_ACTOR_ID_MAX_LENGTH = 128
COPILOT_IDENTIFIER_MAX_LENGTH = 160


def normalize_copilot_actor_id(value: str) -> str:
    normalized = normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")
    if len(normalized) > COPILOT_ACTOR_ID_MAX_LENGTH:
        raise ValueError("COPILOT_ACTOR_TOO_LONG")
    return cast(str, normalized)


def normalize_required_copilot_identifier(value: str, *, error_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_code)
    if len(normalized) > COPILOT_IDENTIFIER_MAX_LENGTH:
        raise ValueError("COPILOT_IDENTIFIER_TOO_LONG")
    return normalized


def normalize_optional_copilot_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_required_copilot_identifier(
        value,
        error_code="COPILOT_IDENTIFIER_REQUIRED",
    )


def normalize_bounded_copilot_string_tuple(
    value: Any,
    *,
    error_code: str,
    max_items: int,
    max_item_length: int,
    allow_empty: bool,
) -> tuple[str, ...]:
    if value is None:
        if allow_empty:
            return ()
        raise ValueError(error_code)
    if not isinstance(value, (list, tuple)):
        raise ValueError(error_code)

    normalized: list[str] = []
    for item in value:
        if len(normalized) >= max_items:
            raise ValueError(error_code)
        if not isinstance(item, str):
            raise ValueError(error_code)
        candidate = item.strip()
        if not candidate:
            raise ValueError(error_code)
        if len(candidate) > max_item_length:
            raise ValueError(error_code)
        if candidate not in normalized:
            normalized.append(candidate)

    if not normalized and not allow_empty:
        raise ValueError(error_code)
    return tuple(normalized)
