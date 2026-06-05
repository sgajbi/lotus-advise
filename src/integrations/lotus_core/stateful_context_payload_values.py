from __future__ import annotations

from collections.abc import Iterable, Iterator
from decimal import Decimal, InvalidOperation
from typing import Any


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def mapping_rows(payload: dict[str, Any], key: str) -> Iterator[dict[str, Any]]:
    rows = payload.get(key, [])
    if not isinstance(rows, Iterable) or isinstance(rows, (str, bytes)):
        return
    for row in rows:
        if isinstance(row, dict):
            yield row


def normalized_text(value: Any) -> str:
    return str(value or "").strip()


def is_cash_asset_class(value: Any) -> bool:
    return normalized_text(value).lower() == "cash"
