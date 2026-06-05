from __future__ import annotations

from typing import Any, cast

from src.core.common.actors import normalize_required_actor_id

COPILOT_ACTOR_ID_MAX_LENGTH = 128
COPILOT_IDENTIFIER_MAX_LENGTH = 160
COPILOT_USER_INSTRUCTION_MAX_LENGTH = 1000


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
    raw_items = _bounded_copilot_sequence(value, error_code=error_code, allow_empty=allow_empty)
    normalized: list[str] = []
    for item in raw_items:
        _append_unique_bounded_copilot_string(
            normalized,
            item,
            error_code=error_code,
            max_items=max_items,
            max_item_length=max_item_length,
        )
    _require_non_empty_copilot_tuple(
        normalized,
        error_code=error_code,
        allow_empty=allow_empty,
    )
    return tuple(normalized)


def _bounded_copilot_sequence(
    value: Any, *, error_code: str, allow_empty: bool
) -> list[Any] | tuple[Any, ...]:
    if value is None:
        if allow_empty:
            return ()
        raise ValueError(error_code)
    if isinstance(value, (list, tuple)):
        return value
    raise ValueError(error_code)


def _append_unique_bounded_copilot_string(
    normalized: list[str],
    item: Any,
    *,
    error_code: str,
    max_items: int,
    max_item_length: int,
) -> None:
    if len(normalized) >= max_items:
        raise ValueError(error_code)
    candidate = _normalize_bounded_copilot_string_item(
        item,
        error_code=error_code,
        max_item_length=max_item_length,
    )
    if candidate not in normalized:
        normalized.append(candidate)


def _normalize_bounded_copilot_string_item(
    item: Any, *, error_code: str, max_item_length: int
) -> str:
    if not isinstance(item, str):
        raise ValueError(error_code)
    candidate = item.strip()
    if not candidate:
        raise ValueError(error_code)
    if len(candidate) > max_item_length:
        raise ValueError(error_code)
    return candidate


def _require_non_empty_copilot_tuple(
    normalized: list[str], *, error_code: str, allow_empty: bool
) -> None:
    if not normalized and not allow_empty:
        raise ValueError(error_code)


def normalize_copilot_user_instruction(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) > COPILOT_USER_INSTRUCTION_MAX_LENGTH:
        raise ValueError("COPILOT_USER_INSTRUCTION_TOO_LONG")
    return normalized
