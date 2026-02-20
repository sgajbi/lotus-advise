import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Optional

from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
)
from src.core.dpm_runs.repository import DpmRunRepository


class SqliteDpmRunRepository(DpmRunRepository):
    def __init__(self, *, database_path: str) -> None:
        self._lock = Lock()
        self._database_path = database_path
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rebalance_run_id) DO UPDATE SET
                correlation_id=excluded.correlation_id,
                request_hash=excluded.request_hash,
                idempotency_key=excluded.idempotency_key,
                portfolio_id=excluded.portfolio_id,
                created_at=excluded.created_at,
                result_json=excluded.result_json
        """
        with self._lock, closing(self._connect()) as connection:
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
            WHERE rebalance_run_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (rebalance_run_id,)).fetchone()
        return self._to_run(row)

    def get_run_by_correlation(self, *, correlation_id: str) -> Optional[DpmRunRecord]:
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
            WHERE correlation_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return self._to_run(row)

    def save_idempotency_mapping(self, record: DpmRunIdempotencyRecord) -> None:
        query = """
            INSERT INTO dpm_run_idempotency (
                idempotency_key,
                request_hash,
                rebalance_run_id,
                created_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(idempotency_key) DO UPDATE SET
                request_hash=excluded.request_hash,
                rebalance_run_id=excluded.rebalance_run_id,
                created_at=excluded.created_at
        """
        with self._lock, closing(self._connect()) as connection:
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
            WHERE idempotency_key = ?
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
            WHERE operation_id = ?
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
            WHERE correlation_id = ?
        """
        with closing(self._connect()) as connection:
            row = connection.execute(query, (correlation_id,)).fetchone()
        return self._to_operation(row)

    def purge_expired_operations(self, *, ttl_seconds: int, now: datetime) -> int:
        cutoff = now.astimezone(timezone.utc) - timedelta(seconds=ttl_seconds)
        query = """
            DELETE FROM dpm_async_operations
            WHERE COALESCE(finished_at, created_at) < ?
        """
        with self._lock, closing(self._connect()) as connection:
            cursor = connection.execute(query, (cutoff.isoformat(),))
            connection.commit()
            return cursor.rowcount

    def append_workflow_decision(self, decision: DpmRunWorkflowDecisionRecord) -> None:
        query = """
            INSERT INTO dpm_workflow_decisions (
                decision_id,
                run_id,
                action,
                reason_code,
                comment,
                actor_id,
                decided_at,
                correlation_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                query,
                (
                    decision.decision_id,
                    decision.run_id,
                    decision.action,
                    decision.reason_code,
                    decision.comment,
                    decision.actor_id,
                    decision.decided_at.isoformat(),
                    decision.correlation_id,
                ),
            )
            connection.commit()

    def list_workflow_decisions(
        self, *, rebalance_run_id: str
    ) -> list[DpmRunWorkflowDecisionRecord]:
        query = """
            SELECT
                decision_id,
                run_id,
                action,
                reason_code,
                comment,
                actor_id,
                decided_at,
                correlation_id
            FROM dpm_workflow_decisions
            WHERE run_id = ?
            ORDER BY decided_at ASC, rowid ASC
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query, (rebalance_run_id,)).fetchall()
        return [
            DpmRunWorkflowDecisionRecord(
                decision_id=row["decision_id"],
                run_id=row["run_id"],
                action=row["action"],
                reason_code=row["reason_code"],
                comment=row["comment"],
                actor_id=row["actor_id"],
                decided_at=datetime.fromisoformat(row["decided_at"]),
                correlation_id=row["correlation_id"],
            )
            for row in rows
        ]

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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(operation_id) DO UPDATE SET
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
        with self._lock, closing(self._connect()) as connection:
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

    def _to_run(self, row: Optional[sqlite3.Row]) -> Optional[DpmRunRecord]:
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

    def _to_operation(self, row: Optional[sqlite3.Row]) -> Optional[DpmAsyncOperationRecord]:
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        Path(self._database_path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dpm_runs (
                    rebalance_run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    idempotency_key TEXT NULL,
                    portfolio_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    result_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dpm_run_idempotency (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    rebalance_run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

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
                );

                CREATE TABLE IF NOT EXISTS dpm_workflow_decisions (
                    decision_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    comment TEXT NULL,
                    actor_id TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    correlation_id TEXT NOT NULL
                );
                """
            )
            connection.commit()


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
