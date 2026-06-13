from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

from src.core.advisory_copilot.business_text import (
    normalize_required_copilot_business_text,
)


def normalize_summary_items(
    value: Any,
    *,
    allow_empty: bool,
    item_limit: int,
    item_max_length: int,
) -> tuple[str, ...]:
    items = _sequence_or_error(value, error_code="COPILOT_EVIDENCE_SUMMARY_INVALID")
    normalized: list[str] = []
    for item in items:
        if len(normalized) >= item_limit:
            raise ValueError("COPILOT_EVIDENCE_SUMMARY_TOO_LARGE")
        normalized.append(_normalized_summary_item(item, item_max_length=item_max_length))
    _assert_summary_size(normalized, allow_empty=allow_empty, item_limit=item_limit)
    return tuple(normalized)


def normalize_unique_literal_items(
    value: Any,
    *,
    allowed: set[str],
    limit: int,
    invalid_error_code: str,
    empty_error_code: str,
    too_large_error_code: str,
) -> tuple[str, ...]:
    items = _sequence_or_error(value, error_code=invalid_error_code)
    normalized: list[str] = []
    for item in items:
        _append_unique_literal(
            normalized,
            item=item,
            allowed=allowed,
            limit=limit,
            invalid_error_code=invalid_error_code,
            too_large_error_code=too_large_error_code,
        )
    if not normalized:
        raise ValueError(empty_error_code)
    return tuple(normalized)


def _sequence_or_error(value: Any, *, error_code: str) -> Iterable[Any]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(error_code)
    return value


def _normalized_summary_item(item: Any, *, item_max_length: int) -> str:
    if not isinstance(item, str):
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_INVALID")
    summary = normalize_required_copilot_business_text(
        item,
        error_code="COPILOT_EVIDENCE_SUMMARY_REQUIRED",
    )
    if len(summary) > item_max_length:
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_TOO_LARGE")
    return cast(str, summary)


def _assert_summary_size(
    normalized: list[str],
    *,
    allow_empty: bool,
    item_limit: int,
) -> None:
    if len(normalized) > item_limit:
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_TOO_LARGE")
    if not normalized and not allow_empty:
        raise ValueError("COPILOT_EVIDENCE_SUMMARY_REQUIRED")


def _append_unique_literal(
    normalized: list[str],
    *,
    item: Any,
    allowed: set[str],
    limit: int,
    invalid_error_code: str,
    too_large_error_code: str,
) -> None:
    if len(normalized) >= limit:
        raise ValueError(too_large_error_code)
    literal = _literal_item(item, allowed=allowed, error_code=invalid_error_code)
    if literal not in normalized:
        normalized.append(literal)


def _literal_item(item: Any, *, allowed: set[str], error_code: str) -> str:
    if not isinstance(item, str):
        raise ValueError(error_code)
    literal = item.strip()
    if literal not in allowed:
        raise ValueError(error_code)
    return literal
