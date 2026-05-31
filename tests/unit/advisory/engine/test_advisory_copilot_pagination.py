from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.core.advisory_copilot.pagination import (
    decode_copilot_run_cursor,
    encode_copilot_run_cursor,
    run_is_after_cursor,
)


def _cursor_payload(**payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def test_copilot_run_cursor_round_trips_aware_timestamp() -> None:
    run = SimpleNamespace(
        run_id="copilot_run_001",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=UTC),
    )

    decoded = decode_copilot_run_cursor(encode_copilot_run_cursor(run))

    assert decoded is not None
    assert decoded.run_id == "copilot_run_001"
    assert decoded.created_at == run.created_at


def test_decode_copilot_run_cursor_allows_non_utc_offsets() -> None:
    cursor = _cursor_payload(
        created_at=datetime(
            2026,
            5,
            28,
            17,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        ).isoformat(),
        run_id="copilot_run_001",
    )

    decoded = decode_copilot_run_cursor(cursor)

    assert decoded is not None
    assert decoded.created_at.utcoffset() == timedelta(hours=8)


def test_decode_copilot_run_cursor_rejects_invalid_shapes() -> None:
    invalid_cursors = [
        "not-a-valid-cursor",
        _cursor_payload(created_at="2026-05-28T09:00:00+00:00"),
        _cursor_payload(created_at="2026-05-28T09:00:00+00:00", run_id=" "),
        _cursor_payload(created_at="2026-05-28T09:00:00+00:00", run_id=None),
        _cursor_payload(created_at=123, run_id="copilot_run_001"),
        _cursor_payload(created_at="2026-05-28T09:00:00", run_id="copilot_run_001"),
        base64.urlsafe_b64encode(b'["not", "an", "object"]').decode("ascii").rstrip("="),
    ]

    for cursor in invalid_cursors:
        with pytest.raises(ValueError, match="COPILOT_RUN_CURSOR_INVALID"):
            decode_copilot_run_cursor(cursor)


def test_run_is_after_cursor_uses_stable_descending_keyset_order() -> None:
    cursor = decode_copilot_run_cursor(
        _cursor_payload(created_at="2026-05-28T09:00:00+00:00", run_id="copilot_run_002")
    )
    assert cursor is not None

    older_run = SimpleNamespace(
        run_id="copilot_run_001",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=UTC),
    )
    newer_run = SimpleNamespace(
        run_id="copilot_run_003",
        created_at=datetime(2026, 5, 28, 9, 0, tzinfo=UTC),
    )

    assert run_is_after_cursor(older_run, cursor) is True
    assert run_is_after_cursor(newer_run, cursor) is False
