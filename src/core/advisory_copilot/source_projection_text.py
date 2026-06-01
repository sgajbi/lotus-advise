from __future__ import annotations

import hashlib
import re
from typing import Any

CONTENT_HASH_MAX_LENGTH = 128
SUMMARY_ITEM_MAX_LENGTH = 1000
REFERENCE_DIGEST_LENGTH = 16


def bounded_projection_reference(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:REFERENCE_DIGEST_LENGTH]
    prefix_length = max_length - REFERENCE_DIGEST_LENGTH - 1
    return f"{normalized[:prefix_length].rstrip('_')}_{digest}"


def projection_identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def projection_summary_item(value: str) -> str:
    return bounded_projection_text(value, max_length=SUMMARY_ITEM_MAX_LENGTH)


def bounded_projection_text(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    suffix = "..."
    return normalized[: max_length - len(suffix)].rstrip() + suffix


def bounded_content_hash(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= CONTENT_HASH_MAX_LENGTH:
        return normalized
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def safe_nested_string(payload: dict[str, Any], *path: str) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current.strip() if isinstance(current, str) and current.strip() else None


def latest_reference(items: list[dict[str, Any]]) -> str | None:
    for item in reversed(items):
        for key in ("report_reference_id", "archive_ref", "archive_reference_id", "event_id"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None
