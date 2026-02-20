import json
from contextlib import closing
from datetime import datetime
from importlib.util import find_spec
from typing import Any, Optional

from src.core.dpm_runs.models import DpmRunRecord


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
            connection.commit()


def _import_psycopg():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


def _json_dump(value: dict) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
