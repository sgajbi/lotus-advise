from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from typing import Any, Optional

from src.core.advisor_cockpit.persistence import (
    CockpitAcknowledgementIdempotencyRecord,
    CockpitAcknowledgementRecord,
)
from src.infrastructure.proposals.postgres_mappers import json_dump

ConnectionFactory = Callable[[], Any]


def get_cockpit_acknowledgement(
    *,
    connect: ConnectionFactory,
    action_item_id: str,
) -> Optional[CockpitAcknowledgementRecord]:
    query = """
        SELECT
            acknowledgement_id,
            action_item_id,
            action_item_version,
            acknowledged_by,
            acknowledged_at,
            acknowledgement_note,
            correlation_id,
            reason_json
        FROM advisor_cockpit_acknowledgements
        WHERE action_item_id = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (action_item_id,)).fetchone()
    if row is None:
        return None
    return CockpitAcknowledgementRecord(
        acknowledgement_id=row["acknowledgement_id"],
        action_item_id=row["action_item_id"],
        action_item_version=int(row["action_item_version"]),
        acknowledged_by=row["acknowledged_by"],
        acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]),
        acknowledgement_note=row["acknowledgement_note"],
        correlation_id=row["correlation_id"],
        reason_json=json.loads(row["reason_json"]),
    )


def save_cockpit_acknowledgement_with_idempotency(
    *,
    connect: ConnectionFactory,
    acknowledgement: CockpitAcknowledgementRecord,
    idempotency: CockpitAcknowledgementIdempotencyRecord,
) -> None:
    idempotency_query = """
        INSERT INTO advisor_cockpit_acknowledgement_idempotency (
            idempotency_key,
            request_hash,
            acknowledgement_id,
            action_item_id,
            created_at
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO NOTHING
    """
    idempotency_lookup = """
        SELECT
            idempotency_key,
            request_hash,
            acknowledgement_id,
            action_item_id,
            created_at
        FROM advisor_cockpit_acknowledgement_idempotency
        WHERE idempotency_key = %s
    """
    acknowledgement_query = """
        INSERT INTO advisor_cockpit_acknowledgements (
            acknowledgement_id,
            action_item_id,
            action_item_version,
            acknowledged_by,
            acknowledged_at,
            acknowledgement_note,
            correlation_id,
            reason_json
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (action_item_id) DO UPDATE SET
            action_item_version=excluded.action_item_version,
            acknowledged_by=excluded.acknowledged_by,
            acknowledged_at=excluded.acknowledged_at,
            acknowledgement_note=excluded.acknowledgement_note,
            correlation_id=excluded.correlation_id,
            reason_json=excluded.reason_json
    """
    with closing(connect()) as connection:
        connection.execute(
            idempotency_query,
            (
                idempotency.idempotency_key,
                idempotency.request_hash,
                idempotency.acknowledgement_id,
                idempotency.action_item_id,
                idempotency.created_at.isoformat(),
            ),
        )
        existing = connection.execute(idempotency_lookup, (idempotency.idempotency_key,)).fetchone()
        if existing is None:
            connection.rollback()
            raise RuntimeError("COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_WRITE_FAILED")
        if (
            existing["request_hash"] != idempotency.request_hash
            or existing["acknowledgement_id"] != idempotency.acknowledgement_id
            or existing["action_item_id"] != idempotency.action_item_id
        ):
            connection.rollback()
            raise ValueError("COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_KEY_CONFLICT")
        connection.execute(
            acknowledgement_query,
            (
                acknowledgement.acknowledgement_id,
                acknowledgement.action_item_id,
                acknowledgement.action_item_version,
                acknowledgement.acknowledged_by,
                acknowledgement.acknowledged_at.isoformat(),
                acknowledgement.acknowledgement_note,
                acknowledgement.correlation_id,
                json_dump(acknowledgement.reason_json),
            ),
        )
        connection.commit()


def get_cockpit_acknowledgement_idempotency(
    *,
    connect: ConnectionFactory,
    idempotency_key: str,
) -> Optional[CockpitAcknowledgementIdempotencyRecord]:
    query = """
        SELECT
            idempotency_key,
            request_hash,
            acknowledgement_id,
            action_item_id,
            created_at
        FROM advisor_cockpit_acknowledgement_idempotency
        WHERE idempotency_key = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (idempotency_key,)).fetchone()
    if row is None:
        return None
    return CockpitAcknowledgementIdempotencyRecord(
        idempotency_key=row["idempotency_key"],
        request_hash=row["request_hash"],
        acknowledgement_id=row["acknowledgement_id"],
        action_item_id=row["action_item_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


__all__ = [
    "get_cockpit_acknowledgement",
    "get_cockpit_acknowledgement_idempotency",
    "save_cockpit_acknowledgement_with_idempotency",
]
