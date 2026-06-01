from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from src.core.proposals.models import ProposalAsyncOperationRecord
from src.infrastructure.proposals.postgres_mappers import (
    json_dump,
    optional_iso,
    optional_json,
    to_operation,
)

ConnectionFactory = Callable[[], Any]


ASYNC_OPERATION_COLUMNS = """
    operation_id,
    operation_type,
    status,
    correlation_id,
    idempotency_key,
    proposal_id,
    created_by,
    created_at,
    payload_json,
    attempt_count,
    max_attempts,
    started_at,
    lease_expires_at,
    finished_at,
    result_json,
    error_json
"""


def upsert_operation(
    *,
    connect: ConnectionFactory,
    operation: ProposalAsyncOperationRecord,
) -> None:
    query = f"""
        INSERT INTO proposal_async_operations (
            {ASYNC_OPERATION_COLUMNS}
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (operation_id) DO UPDATE SET
            operation_type=excluded.operation_type,
            status=excluded.status,
            correlation_id=excluded.correlation_id,
            idempotency_key=excluded.idempotency_key,
            proposal_id=excluded.proposal_id,
            created_by=excluded.created_by,
            created_at=excluded.created_at,
            payload_json=excluded.payload_json,
            attempt_count=excluded.attempt_count,
            max_attempts=excluded.max_attempts,
            started_at=excluded.started_at,
            lease_expires_at=excluded.lease_expires_at,
            finished_at=excluded.finished_at,
            result_json=excluded.result_json,
            error_json=excluded.error_json
    """
    with closing(connect()) as connection:
        connection.execute(query, _operation_params(operation))
        connection.commit()


def create_operation_if_absent_by_idempotency(
    *,
    connect: ConnectionFactory,
    operation: ProposalAsyncOperationRecord,
) -> tuple[ProposalAsyncOperationRecord, bool]:
    if not operation.idempotency_key:
        upsert_operation(connect=connect, operation=operation)
        return deepcopy(operation), True

    query = f"""
        WITH inserted AS (
            INSERT INTO proposal_async_operations (
                {ASYNC_OPERATION_COLUMNS}
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
            RETURNING
                {ASYNC_OPERATION_COLUMNS}
        )
        SELECT * FROM inserted
        UNION ALL
        SELECT
            {ASYNC_OPERATION_COLUMNS}
        FROM proposal_async_operations
        WHERE idempotency_key = %s
        LIMIT 1
    """
    params = (*_operation_params(operation), operation.idempotency_key)
    with closing(connect()) as connection:
        row = connection.execute(query, params).fetchone()
        connection.commit()
    stored = to_operation(row)
    assert stored is not None
    return stored, stored.operation_id == operation.operation_id


def get_operation(
    *,
    connect: ConnectionFactory,
    operation_id: str,
) -> Optional[ProposalAsyncOperationRecord]:
    query = f"""
        SELECT
            {ASYNC_OPERATION_COLUMNS}
        FROM proposal_async_operations
        WHERE operation_id = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (operation_id,)).fetchone()
    return to_operation(row)


def get_operation_by_correlation(
    *,
    connect: ConnectionFactory,
    correlation_id: str,
) -> Optional[ProposalAsyncOperationRecord]:
    query = f"""
        SELECT
            {ASYNC_OPERATION_COLUMNS}
        FROM proposal_async_operations
        WHERE correlation_id = %s
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (correlation_id,)).fetchone()
    return to_operation(row)


def get_operation_by_idempotency(
    *,
    connect: ConnectionFactory,
    idempotency_key: str,
) -> Optional[ProposalAsyncOperationRecord]:
    query = f"""
        SELECT
            {ASYNC_OPERATION_COLUMNS}
        FROM proposal_async_operations
        WHERE idempotency_key = %s
        ORDER BY created_at DESC, operation_id DESC
        LIMIT 1
    """
    with closing(connect()) as connection:
        row = connection.execute(query, (idempotency_key,)).fetchone()
    return to_operation(row)


def list_recoverable_operations(
    *,
    connect: ConnectionFactory,
    as_of: datetime,
    limit: Optional[int] = None,
) -> list[ProposalAsyncOperationRecord]:
    if limit is not None and limit <= 0:
        return []
    args: list[object] = [as_of.isoformat()]
    query = f"""
        SELECT
            {ASYNC_OPERATION_COLUMNS}
        FROM proposal_async_operations
        WHERE
            status = 'PENDING'
            OR (
                status = 'RUNNING'
                AND finished_at IS NULL
                AND lease_expires_at IS NOT NULL
                AND lease_expires_at <= %s
            )
        ORDER BY created_at ASC, operation_id ASC
    """
    if limit is not None:
        query = f"{query}\nLIMIT %s"
        args.append(limit)
    with closing(connect()) as connection:
        rows = connection.execute(query, tuple(args)).fetchall()
    return [operation for operation in (to_operation(row) for row in rows) if operation is not None]


def _operation_params(operation: ProposalAsyncOperationRecord) -> tuple[object, ...]:
    return (
        operation.operation_id,
        operation.operation_type,
        operation.status,
        operation.correlation_id,
        operation.idempotency_key,
        operation.proposal_id,
        operation.created_by,
        operation.created_at.isoformat(),
        json_dump(operation.payload_json),
        operation.attempt_count,
        operation.max_attempts,
        optional_iso(operation.started_at),
        optional_iso(operation.lease_expires_at),
        optional_iso(operation.finished_at),
        optional_json(operation.result_json),
        optional_json(operation.error_json),
    )


__all__ = [
    "create_operation_if_absent_by_idempotency",
    "get_operation",
    "get_operation_by_correlation",
    "get_operation_by_idempotency",
    "list_recoverable_operations",
    "upsert_operation",
]
