from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime

from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord

_INVALID_CURSOR = "COPILOT_RUN_CURSOR_INVALID"
COPILOT_RUN_DEFAULT_PAGE_SIZE = 25
COPILOT_RUN_MAX_PAGE_SIZE = 100
_INVALID_PAGE_SIZE = "COPILOT_RUN_PAGE_SIZE_INVALID"


@dataclass(frozen=True)
class AdvisoryCopilotRunCursor:
    created_at: datetime
    run_id: str


def encode_copilot_run_cursor(run: AdvisoryCopilotRunRecord) -> str:
    payload = {
        "created_at": run.created_at.isoformat(),
        "run_id": run.run_id,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def decode_copilot_run_cursor(cursor: str | None) -> AdvisoryCopilotRunCursor | None:
    if cursor is None:
        return None
    try:
        padded = cursor + ("=" * (-len(cursor) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
    except (binascii.Error, json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(_INVALID_CURSOR) from exc

    if not isinstance(payload, dict):
        raise ValueError(_INVALID_CURSOR)

    raw_created_at = payload.get("created_at")
    raw_run_id = payload.get("run_id")
    if not isinstance(raw_created_at, str) or not isinstance(raw_run_id, str):
        raise ValueError(_INVALID_CURSOR)

    try:
        created_at = datetime.fromisoformat(raw_created_at)
    except ValueError as exc:
        raise ValueError(_INVALID_CURSOR) from exc

    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError(_INVALID_CURSOR)

    run_id = raw_run_id.strip()
    if not run_id:
        raise ValueError(_INVALID_CURSOR)
    return AdvisoryCopilotRunCursor(created_at=created_at, run_id=run_id)


def normalize_copilot_run_page_size(limit: int | None) -> int:
    if limit is None:
        return COPILOT_RUN_DEFAULT_PAGE_SIZE
    if limit < 1:
        raise ValueError(_INVALID_PAGE_SIZE)
    return min(limit, COPILOT_RUN_MAX_PAGE_SIZE)


def run_is_after_cursor(
    run: AdvisoryCopilotRunRecord,
    cursor: AdvisoryCopilotRunCursor | None,
) -> bool:
    if cursor is None:
        return True
    return (run.created_at, run.run_id) < (cursor.created_at, cursor.run_id)
