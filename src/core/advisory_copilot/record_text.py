from __future__ import annotations

from typing import Any


def normalize_required_record_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def normalize_optional_record_text(value: str | None, *, error_code: str) -> str | None:
    if value is None:
        return None
    return normalize_required_record_text(value, error_code=error_code)


def normalize_bounded_record_text_list(
    value: Any,
    *,
    max_items: int,
    max_item_length: int,
    error_code: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error_code)
    normalized: list[str] = []
    for item in value:
        _ensure_record_text_list_capacity(normalized, max_items=max_items, error_code=error_code)
        normalized.append(
            _normalize_bounded_record_text_item(
                item,
                max_item_length=max_item_length,
                error_code=error_code,
            )
        )
    return normalized


def _ensure_record_text_list_capacity(
    normalized: list[str],
    *,
    max_items: int,
    error_code: str,
) -> None:
    if len(normalized) >= max_items:
        raise ValueError(error_code)


def _normalize_bounded_record_text_item(
    item: Any,
    *,
    max_item_length: int,
    error_code: str,
) -> str:
    if not isinstance(item, str):
        raise ValueError(error_code)
    text = normalize_required_record_text(item, error_code=error_code)
    if len(text) > max_item_length:
        raise ValueError(error_code)
    return text
