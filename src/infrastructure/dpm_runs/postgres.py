import json
from contextlib import closing
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
from typing import Any, Optional

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
)


class PostgresDpmRunRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED")
        if find_spec("psycopg") is None:
            raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING")
        self._dsn = dsn
        self._init_db()

    def save_run(self, run: DpmRunRecord) -> None:
        query = """
            INSERT INTO dpm_runs (
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (rebalance_run_id) DO UPDATE SET
                correlation_id=excluded.correlation_id,
                request_hash=excluded.request_hash,
                idempotency_key=excluded.idempotency_key,
                portfolio_id=excluded.portfolio_id,
                created_at=excluded.created_at,
                result_json=excluded.result_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    run.rebalance_run_id,
                    run.correlation_id,
                    run.request_hash,
                    run.idempotency_key,
                    run.portfolio_id,
                    run.created_at.isoformat(),
                    _json_dump(run.result_json),
                ),
            )
            connection.commit()

    def get_run(self, *, rebalance_run_id: str) -> Optional[DpmRunRecord]:
        query = """
            SELECT
                rebalance_run_id,
                correlation_id,
                request_hash,
                idempotency_key,
                portfolio_id,
                created_at,
                result_json
            FROM dpm_runs
            WHERE rebalance_run_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (rebalance_run_id,)).fetchone()
        if row is None:
            return None
        return DpmRunRecord(
            rebalance_run_id=row["rebalance_run_id"],
            correlation_id=row["correlation_id"],
            request_hash=row["request_hash"],
            idempotency_key=row["idempotency_key"],
            portfolio_id=row["portfolio_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            result_json=json.loads(row["result_json"]),
        )

    def save_run_artifact(self, *, rebalance_run_id: str, artifact_json: dict[str, Any]) -> None:
        query = """
            INSERT INTO dpm_run_artifacts (
                rebalance_run_id,
                artifact_json
            ) VALUES (%s, %s)
            ON CONFLICT (rebalance_run_id) DO UPDATE SET
                artifact_json=excluded.artifact_json
        """
        with closing(self._connect()) as connection:
            connection.execute(query, (rebalance_run_id, _json_dump(artifact_json)))
            connection.commit()

    def get_run_artifact(self, *, rebalance_run_id: str) -> Optional[dict[str, Any]]:
        query = """
            SELECT artifact_json
            FROM dpm_run_artifacts
            WHERE rebalance_run_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (rebalance_run_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row["artifact_json"])

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None:
        query = """
            INSERT INTO dpm_run_idempotency (
                idempotency_key,
                request_hash,
                rebalance_run_id,
                created_at
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (idempotency_key) DO UPDATE SET
                request_hash=excluded.request_hash,
                rebalance_run_id=excluded.rebalance_run_id,
                created_at=excluded.created_at
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    record.idempotency_key,
                    record.request_hash,
                    record.rebalance_run_id,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def get_idempotency_mapping(self, *, idempotency_key: str) -> Optional[DpmRunIdempotencyRecord]:
        query = """
            SELECT
                idempotency_key,
                request_hash,
                rebalance_run_id,
                created_at
            FROM dpm_run_idempotency
            WHERE idempotency_key = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (idempotency_key,)).fetchone()
        if row is None:
            return None
        return DpmRunIdempotencyRecord(
            idempotency_key=row["idempotency_key"],
            request_hash=row["request_hash"],
            rebalance_run_id=row["rebalance_run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def append_idempotency_history(self, record: DpmRunIdempotencyHistoryRecord) -> None:
        query = """
            INSERT INTO dpm_run_idempotency_history (
                idempotency_key,
                rebalance_run_id,
                correlation_id,
                request_hash,
                created_at
            ) VALUES (%s, %s, %s, %s, %s)
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    record.idempotency_key,
                    record.rebalance_run_id,
                    record.correlation_id,
                    record.request_hash,
                    record.created_at.isoformat(),
                ),
            )
            connection.commit()

    def list_idempotency_history(
        self, *, idempotency_key: str
    ) -> list[DpmRunIdempotencyHistoryRecord]:
        query = """
            SELECT
                idempotency_key,
                rebalance_run_id,
                correlation_id,
                request_hash,
                created_at
            FROM dpm_run_idempotency_history
            WHERE idempotency_key = %s
            ORDER BY created_at ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (idempotency_key,)).fetchall()
        return [
            DpmRunIdempotencyHistoryRecord(
                idempotency_key=row["idempotency_key"],
                rebalance_run_id=row["rebalance_run_id"],
                correlation_id=row["correlation_id"],
                request_hash=row["request_hash"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def create_operation(self, operation: DpmAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def update_operation(self, operation: DpmAsyncOperationRecord) -> None:
        self._upsert_operation(operation)

    def get_operation(self, *, operation_id: str) -> Optional[DpmAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            WHERE operation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (operation_id,)).fetchone()
        return self._to_operation(row)

    def get_operation_by_correlation(
        self, *, correlation_id: str
    ) -> Optional[DpmAsyncOperationRecord]:
        query = """
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            WHERE correlation_id = %s
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return self._to_operation(row)

    def list_operations(
        self,
        *,
        created_from: Optional[datetime],
        created_to: Optional[datetime],
        operation_type: Optional[str],
        status: Optional[str],
        correlation_id: Optional[str],
        limit: int,
        cursor: Optional[str],
    ) -> tuple[list[DpmAsyncOperationRecord], Optional[str]]:
        where_clauses = []
        args: list[str] = []
        if created_from is not None:
            where_clauses.append("created_at >= %s")
            args.append(created_from.isoformat())
        if created_to is not None:
            where_clauses.append("created_at <= %s")
            args.append(created_to.isoformat())
        if operation_type is not None:
            where_clauses.append("operation_type = %s")
            args.append(operation_type)
        if status is not None:
            where_clauses.append("status = %s")
            args.append(status)
        if correlation_id is not None:
            where_clauses.append("correlation_id = %s")
            args.append(correlation_id)
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            FROM dpm_async_operations
            {where_sql}
            ORDER BY created_at DESC, operation_id DESC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, tuple(args)).fetchall()
        operations = [self._to_operation(row) for row in rows]
        operations = [operation for operation in operations if operation is not None]
        if cursor is not None:
            cursor_index = next(
                (index for index, row in enumerate(operations) if row.operation_id == cursor),
                None,
            )
            if cursor_index is None:
                return [], None
            operations = operations[cursor_index + 1 :]
        page = operations[:limit]
        next_cursor = page[-1].operation_id if len(operations) > limit else None
        return page, next_cursor

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int:
        cutoff = now.astimezone(timezone.utc) - timedelta(seconds=ttl_seconds)
        query = """
            DELETE FROM dpm_async_operations
            WHERE COALESCE(finished_at, created_at) < %s
        """
        with closing(self._connect()) as connection:
            cursor = connection.execute(query, (cutoff.isoformat(),))
            connection.commit()
            return cursor.rowcount

    def __getattr__(self, _name: str):
        raise RuntimeError("DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED")

    def _connect(self):
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dpm_runs (
                    rebalance_run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    idempotency_key TEXT NULL,
                    portfolio_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dpm_run_artifacts (
                    rebalance_run_id TEXT PRIMARY KEY,
                    artifact_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dpm_run_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    rebalance_run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dpm_run_idempotency_history (
                    idempotency_key TEXT NOT NULL,
                    rebalance_run_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dpm_async_operations (
                    operation_id TEXT PRIMARY KEY,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    correlation_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    finished_at TEXT NULL,
                    result_json TEXT NULL,
                    error_json TEXT NULL,
                    request_json TEXT NULL
                )
                """
            )
            connection.commit()

    def _upsert_operation(self, operation: DpmAsyncOperationRecord) -> None:
        query = """
            INSERT INTO dpm_async_operations (
                operation_id,
                operation_type,
                status,
                correlation_id,
                created_at,
                started_at,
                finished_at,
                result_json,
                error_json,
                request_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (operation_id) DO UPDATE SET
                operation_type=excluded.operation_type,
                status=excluded.status,
                correlation_id=excluded.correlation_id,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                finished_at=excluded.finished_at,
                result_json=excluded.result_json,
                error_json=excluded.error_json,
                request_json=excluded.request_json
        """
        with closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    operation.operation_id,
                    operation.operation_type,
                    operation.status,
                    operation.correlation_id,
                    operation.created_at.isoformat(),
                    _optional_iso(operation.started_at),
                    _optional_iso(operation.finished_at),
                    _optional_json(operation.result_json),
                    _optional_json(operation.error_json),
                    _optional_json(operation.request_json),
                ),
            )
            connection.commit()

    def _to_operation(self, row) -> Optional[DpmAsyncOperationRecord]:
        if row is None:
            return None
        return DpmAsyncOperationRecord(
            operation_id=row["operation_id"],
            operation_type=row["operation_type"],
            status=row["status"],
            correlation_id=row["correlation_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=_optional_datetime(row["started_at"]),
            finished_at=_optional_datetime(row["finished_at"]),
            result_json=_optional_load_json(row["result_json"]),
            error_json=_optional_load_json(row["error_json"]),
            request_json=_optional_load_json(row["request_json"]),
        )


def _import_psycopg():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _json_dump(value: dict) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _optional_json(value: Optional[dict]) -> Optional[str]:
    if value is None:
        return None
    return _json_dump(value)


def _optional_load_json(value: Optional[str]) -> Optional[dict]:
    if value is None:
        return None
    return json.loads(value)


def _optional_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def _optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)
