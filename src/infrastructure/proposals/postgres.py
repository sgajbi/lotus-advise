import json
from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from typing import Optional

from src.core.proposals.models import ProposalAsyncOperationRecord, ProposalIdempotencyRecord


class PostgresProposalRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("PROPOSAL_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def get_idempotency(self, *, idempotency_key: str) -> Optional[ProposalIdempotencyRecord]:
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
        with closing(self._connect()) as connection:
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

    def save_idempotency(self, record: ProposalIdempotencyRecord) -> None:
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
        with closing(self._connect()) as connection:
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
            connection.commit()

    def create_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def update_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def get_operation(self, *, operation_id: str) -> Optional[ProposalAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            FROM proposal_async_operations
            WHERE operation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (operation_id,)).fetchone()
        return _to_operation(row)

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[ProposalAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            FROM proposal_async_operations
            WHERE correlation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return _to_operation(row)

    def __getattr__(self, _name: str):
        raise RuntimeError("PROPOSAL_POSTGRES_NOT_IMPLEMENTED")

    def _connect(self):
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    proposal_id TEXT NOT NULL,
                    proposal_version_no INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS proposal_async_operations (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT NULL,
                    proposal_id TEXT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    finished_at TEXT NULL,
                    result_json TEXT NULL,
                    error_json TEXT NULL
                )
                """
            )
            connection.commit()

    def _upsert_operation(self, operation: ProposalAsyncOperationRecord) -> None:
        query = """
            INSERT INTO proposal_async_operations (
                operation_id,
                operation_type,
                status,
                correlation_id,
                idempotency_key,
                proposal_id,
                created_by,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (operation_id) DO UPDATE SET
                operation_type=excluded.operation_type,
                status=excluded.status,
                correlation_id=excluded.correlation_id,
                idempotency_key=excluded.idempotency_key,
                proposal_id=excluded.proposal_id,
                created_by=excluded.created_by,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                result_json=excluded.result_json,
                error_json=excluded.error_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    operation.operation_id,
                    operation.operation_type,
                    operation.status,
                    operation.correlation_id,
                    operation.idempotency_key,
                    operation.proposal_id,
                    operation.created_by,
                    operation.created_at.isoformat(),
                    _optional_iso(operation.started_at),
                    _optional_iso(operation.finished_at),
                    _optional_json(operation.result_json),
                    _optional_json(operation.error_json),
                ),
            )
            connection.commit()


def _import_psycopg():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _optional_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _optional_json(value: Optional[dict]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _to_operation(row) -> Optional[ProposalAsyncOperationRecord]:
    if row is None:
        return None
    return ProposalAsyncOperationRecord(
        operation_id=row["operation_id"],
        operation_type=row["operation_type"],
        status=row["status"],
        correlation_id=row["correlation_id"],
        idempotency_key=row["idempotency_key"],
        proposal_id=row["proposal_id"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        started_at=_optional_datetime(row["started_at"]),
        finished_at=_optional_datetime(row["finished_at"]),
        result_json=_optional_load_json(row["result_json"]),
        error_json=_optional_load_json(row["error_json"]),
    )


def _optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _optional_load_json(value: Optional[str]) -> Optional[dict]:
    if value is None:
        return None
    return json.loads(value)
