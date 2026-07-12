from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from typing import Any, Optional

from src.core.proposals.models import (
    ProposalIdempotencyRecord,
    ProposalMemoIdempotencyRecord,
    ProposalSimulationIdempotencyRecord,
)
from src.infrastructure.proposals.postgres_mappers import json_dump

ConnectionFactory = Callable[[], Any]


def get_proposal_idempotency(
    *,
    connect: ConnectionFactory,
    idempotency_key: str,
) -> Optional[ProposalIdempotencyRecord]:
    query = """
        SELECT
            idempotency_key,
            request_hash,
            proposal_id,
            proposal_version_no,
            created_at
        FROM proposal_idempotency
        WHERE idempotency_key = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (idempotency_key,)).fetchone()
    if row is None:
        return None
    return ProposalIdempotencyRecord(
        idempotency_key=row["idempotency_key"],
        request_hash=row["request_hash"],
        proposal_id=row["proposal_id"],
        proposal_version_no=int(row["proposal_version_no"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def save_proposal_idempotency(
    *,
    connect: ConnectionFactory,
    record: ProposalIdempotencyRecord,
) -> None:
    with closing(connect()) as connection:
        insert_proposal_idempotency(connection=connection, record=record)
        connection.commit()


def insert_proposal_idempotency(*, connection: Any, record: ProposalIdempotencyRecord) -> None:
    query = """
        INSERT INTO proposal_idempotency (
            idempotency_key,
            request_hash,
            proposal_id,
            proposal_version_no,
            created_at
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE SET
            request_hash=excluded.request_hash,
            proposal_id=excluded.proposal_id,
            proposal_version_no=excluded.proposal_version_no,
            created_at=excluded.created_at
    """
    connection.execute(
        query,
        (
            record.idempotency_key,
            record.request_hash,
            record.proposal_id,
            record.proposal_version_no,
            record.created_at.isoformat(),
        ),
    )


def get_simulation_idempotency(
    *,
    connect: ConnectionFactory,
    idempotency_key: str,
) -> Optional[ProposalSimulationIdempotencyRecord]:
    query = """
        SELECT
            idempotency_key,
            request_hash,
            response_json,
            created_at
        FROM proposal_simulation_idempotency
        WHERE idempotency_key = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (idempotency_key,)).fetchone()
    if row is None:
        return None
    return ProposalSimulationIdempotencyRecord(
        idempotency_key=row["idempotency_key"],
        request_hash=row["request_hash"],
        response_json=json.loads(row["response_json"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def save_simulation_idempotency(
    *,
    connect: ConnectionFactory,
    record: ProposalSimulationIdempotencyRecord,
) -> None:
    query = """
        INSERT INTO proposal_simulation_idempotency (
            idempotency_key,
            request_hash,
            response_json,
            created_at
        ) VALUES (%s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO UPDATE SET
            request_hash=excluded.request_hash,
            response_json=excluded.response_json,
            created_at=excluded.created_at
    """
    with closing(connect()) as connection:
        connection.execute(
            query,
            (
                record.idempotency_key,
                record.request_hash,
                json_dump(record.response_json),
                record.created_at.isoformat(),
            ),
        )
        connection.commit()


def get_memo_idempotency(
    *,
    connect: ConnectionFactory,
    idempotency_key: str,
) -> Optional[ProposalMemoIdempotencyRecord]:
    query = """
        SELECT
            idempotency_key,
            request_hash,
            memo_id,
            proposal_id,
            proposal_version_no,
            created_at
        FROM proposal_memo_idempotency
        WHERE idempotency_key = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (idempotency_key,)).fetchone()
    if row is None:
        return None
    return ProposalMemoIdempotencyRecord(
        idempotency_key=row["idempotency_key"],
        request_hash=row["request_hash"],
        memo_id=row["memo_id"],
        proposal_id=row["proposal_id"],
        proposal_version_no=int(row["proposal_version_no"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def save_memo_idempotency(
    *,
    connect: ConnectionFactory,
    record: ProposalMemoIdempotencyRecord,
) -> None:
    query = """
        INSERT INTO proposal_memo_idempotency (
            idempotency_key,
            request_hash,
            memo_id,
            proposal_id,
            proposal_version_no,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (idempotency_key) DO NOTHING
    """
    with closing(connect()) as connection:
        connection.execute(
            query,
            (
                record.idempotency_key,
                record.request_hash,
                record.memo_id,
                record.proposal_id,
                record.proposal_version_no,
                record.created_at.isoformat(),
            ),
        )
        connection.commit()


__all__ = [
    "get_memo_idempotency",
    "get_proposal_idempotency",
    "get_simulation_idempotency",
    "insert_proposal_idempotency",
    "save_memo_idempotency",
    "save_proposal_idempotency",
    "save_simulation_idempotency",
]
