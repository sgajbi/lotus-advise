from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime

from src.core.advisory_copilot.records import AdvisoryCopilotRunRecord


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
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        run_id = str(payload["run_id"]).strip()
    except Exception as exc:
        raise ValueError("COPILOT_RUN_CURSOR_INVALID") from exc
    if not run_id:
        raise ValueError("COPILOT_RUN_CURSOR_INVALID")
    return AdvisoryCopilotRunCursor(created_at=created_at, run_id=run_id)


def run_is_after_cursor(
    run: AdvisoryCopilotRunRecord,
    cursor: AdvisoryCopilotRunCursor | None,
) -> bool:
    if cursor is None:
        return True
    return (run.created_at, run.run_id) < (cursor.created_at, cursor.run_id)
