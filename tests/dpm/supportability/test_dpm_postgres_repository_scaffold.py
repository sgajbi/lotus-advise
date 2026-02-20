from datetime import datetime, timezone
from types import ModuleType

import src.infrastructure.dpm_runs.postgres as postgres_module
from src.core.dpm_runs.models import (
    DpmAsyncOperationRecord,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyRecord,
    DpmRunRecord,
)
from src.infrastructure.dpm_runs.postgres import (
    PostgresDpmRunRepository,
    _import_psycopg,
    _json_dump,
)


class _FakeCursor:
    def __init__(self, row=None, rows=None, rowcount=0):
        self._row = row
        self._rows = rows or []
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self):
        self.runs = {}
        self.artifacts = {}
        self.idempotency = {}
        self.idempotency_history = []
        self.operations = {}
        self.commits = 0

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql.startswith("CREATE TABLE"):
            return _FakeCursor(None)
        if "INSERT INTO dpm_runs" in sql:
            row = {
                "rebalance_run_id": args[0],
                "correlation_id": args[1],
                "request_hash": args[2],
                "idempotency_key": args[3],
                "portfolio_id": args[4],
                "created_at": args[5],
                "result_json": args[6],
            }
            self.runs[args[0]] = row
            return _FakeCursor(None)
        if "FROM dpm_runs" in sql:
            return _FakeCursor(self.runs.get(args[0]))
        if "INSERT INTO dpm_run_artifacts" in sql:
            self.artifacts[args[0]] = {"artifact_json": args[1]}
            return _FakeCursor(None)
        if "FROM dpm_run_artifacts" in sql:
            return _FakeCursor(self.artifacts.get(args[0]))
        if "INSERT INTO dpm_run_idempotency (" in sql:
            row = {
                "idempotency_key": args[0],
                "request_hash": args[1],
                "rebalance_run_id": args[2],
                "created_at": args[3],
            }
            self.idempotency[args[0]] = row
            return _FakeCursor()
        if "FROM dpm_run_idempotency WHERE idempotency_key = %s" in sql:
            return _FakeCursor(self.idempotency.get(args[0]))
        if "INSERT INTO dpm_run_idempotency_history (" in sql:
            self.idempotency_history.append(
                {
                    "idempotency_key": args[0],
                    "rebalance_run_id": args[1],
                    "correlation_id": args[2],
                    "request_hash": args[3],
                    "created_at": args[4],
                }
            )
            return _FakeCursor()
        if "FROM dpm_run_idempotency_history" in sql:
            rows = [row for row in self.idempotency_history if row["idempotency_key"] == args[0]]
            rows = sorted(rows, key=lambda row: row["created_at"])
            return _FakeCursor(rows=rows)
        if "INSERT INTO dpm_async_operations (" in sql:
            row = {
                "operation_id": args[0],
                "operation_type": args[1],
                "status": args[2],
                "correlation_id": args[3],
                "created_at": args[4],
                "started_at": args[5],
                "finished_at": args[6],
                "result_json": args[7],
                "error_json": args[8],
                "request_json": args[9],
            }
            self.operations[args[0]] = row
            return _FakeCursor()
        if "FROM dpm_async_operations WHERE operation_id = %s" in sql:
            return _FakeCursor(self.operations.get(args[0]))
        if "FROM dpm_async_operations WHERE correlation_id = %s" in sql:
            row = next(
                (
                    operation
                    for operation in self.operations.values()
                    if operation["correlation_id"] == args[0]
                ),
                None,
            )
            return _FakeCursor(row)
        if "FROM dpm_async_operations" in sql and "ORDER BY created_at DESC" in sql:
            rows = list(self.operations.values())
            arg_index = 0
            if "created_at >= %s" in sql:
                created_from = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] >= created_from]
            if "created_at <= %s" in sql:
                created_to = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["created_at"] <= created_to]
            if "operation_type = %s" in sql:
                operation_type = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["operation_type"] == operation_type]
            if "status = %s" in sql:
                status = args[arg_index]
                arg_index += 1
                rows = [row for row in rows if row["status"] == status]
            if "correlation_id = %s" in sql:
                correlation_id = args[arg_index]
                rows = [row for row in rows if row["correlation_id"] == correlation_id]
            rows = sorted(
                rows,
                key=lambda row: (row["created_at"], row["operation_id"]),
                reverse=True,
            )
            return _FakeCursor(rows=rows)
        if "DELETE FROM dpm_async_operations" in sql:
            cutoff = args[0]
            to_remove = []
            for operation_id, row in self.operations.items():
                anchor = row["finished_at"] or row["created_at"]
                if anchor < cutoff:
                    to_remove.append(operation_id)
            for operation_id in to_remove:
                self.operations.pop(operation_id, None)
            return _FakeCursor(rowcount=len(to_remove))
        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.commits += 1

    def close(self):
        return None


def _build_repository(monkeypatch):
    fake_connection = _FakeConnection()
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: object())
    monkeypatch.setattr(
        PostgresDpmRunRepository,
        "_connect",
        lambda self: fake_connection,
    )
    repository = PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    return repository, fake_connection


def test_postgres_repository_requires_dsn():
    try:
        PostgresDpmRunRepository(dsn="")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DSN_REQUIRED"
    else:
        raise AssertionError("Expected RuntimeError for missing DSN")


def test_postgres_repository_requires_driver(monkeypatch):
    monkeypatch.setattr(postgres_module, "find_spec", lambda _name: None)
    try:
        PostgresDpmRunRepository(dsn="postgresql://user:pass@localhost:5432/dpm")
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_DRIVER_MISSING"
    else:
        raise AssertionError("Expected RuntimeError for missing psycopg driver")


def test_postgres_repository_save_and_get_run(monkeypatch):
    repository, connection = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    run = DpmRunRecord(
        rebalance_run_id="rr_pg_1",
        correlation_id="corr_pg_1",
        request_hash="sha256:req-pg-1",
        idempotency_key="idem_pg_1",
        portfolio_id="pf_pg_1",
        created_at=now,
        result_json={"rebalance_run_id": "rr_pg_1", "status": "READY"},
    )
    repository.save_run(run)
    stored = repository.get_run(rebalance_run_id="rr_pg_1")
    assert stored is not None
    assert stored.rebalance_run_id == "rr_pg_1"
    assert stored.result_json["status"] == "READY"
    assert repository.get_run(rebalance_run_id="rr_pg_missing") is None
    assert connection.commits >= 2


def test_postgres_repository_save_and_get_artifact(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    artifact = {"artifact_id": "dra_pg_1", "evidence": {"hashes": {"artifact_hash": "sha256:1"}}}
    repository.save_run_artifact(rebalance_run_id="rr_pg_1", artifact_json=artifact)
    stored = repository.get_run_artifact(rebalance_run_id="rr_pg_1")
    assert stored == artifact
    assert repository.get_run_artifact(rebalance_run_id="rr_pg_missing") is None


def test_postgres_repository_save_and_get_idempotency_mapping(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    record = DpmRunIdempotencyRecord(
        idempotency_key="idem_pg_1",
        request_hash="sha256:req-pg-1",
        rebalance_run_id="rr_pg_1",
        created_at=now,
    )
    repository.save_idempotency_mapping(record)
    stored = repository.get_idempotency_mapping(idempotency_key="idem_pg_1")
    assert stored is not None
    assert stored.rebalance_run_id == "rr_pg_1"
    assert repository.get_idempotency_mapping(idempotency_key="idem_pg_missing") is None


def test_postgres_repository_append_and_list_idempotency_history(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    one = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_pg_history",
        rebalance_run_id="rr_pg_1",
        correlation_id="corr_pg_1",
        request_hash="sha256:req-pg-1",
        created_at=now,
    )
    two = DpmRunIdempotencyHistoryRecord(
        idempotency_key="idem_pg_history",
        rebalance_run_id="rr_pg_2",
        correlation_id="corr_pg_2",
        request_hash="sha256:req-pg-2",
        created_at=now.replace(minute=1),
    )
    repository.append_idempotency_history(one)
    repository.append_idempotency_history(two)
    history = repository.list_idempotency_history(idempotency_key="idem_pg_history")
    assert [row.rebalance_run_id for row in history] == ["rr_pg_1", "rr_pg_2"]
    assert repository.list_idempotency_history(idempotency_key="idem_pg_history_missing") == []


def test_postgres_repository_create_update_get_operation(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    operation = DpmAsyncOperationRecord(
        operation_id="dop_pg_1",
        operation_type="ANALYZE_SCENARIOS",
        status="PENDING",
        correlation_id="corr_op_pg_1",
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
        request_json={"scenarios": {"baseline": {"options": {}}}},
    )
    repository.create_operation(operation)
    stored = repository.get_operation(operation_id="dop_pg_1")
    assert stored is not None
    assert stored.status == "PENDING"

    operation.status = "SUCCEEDED"
    operation.started_at = now.replace(second=1)
    operation.finished_at = now.replace(second=2)
    operation.result_json = {"ok": True}
    operation.request_json = None
    repository.update_operation(operation)
    by_correlation = repository.get_operation_by_correlation(correlation_id="corr_op_pg_1")
    assert by_correlation is not None
    assert by_correlation.status == "SUCCEEDED"
    assert by_correlation.result_json == {"ok": True}
    assert repository.get_operation(operation_id="dop_pg_missing") is None
    assert repository.get_operation_by_correlation(correlation_id="corr_op_pg_missing") is None


def test_postgres_repository_list_operations_and_purge(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_1",
            operation_type="ANALYZE_SCENARIOS",
            status="PENDING",
            correlation_id="corr_op_pg_1",
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json=None,
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_op_pg_2",
            created_at=now.replace(minute=1),
            started_at=now.replace(minute=1, second=1),
            finished_at=now.replace(minute=1, second=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )
    rows, next_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=None,
    )
    assert [row.operation_id for row in rows] == ["dop_pg_2"]
    assert next_cursor == "dop_pg_2"

    rows_two, cursor_two = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type="ANALYZE_SCENARIOS",
        status=None,
        correlation_id=None,
        limit=1,
        cursor=next_cursor,
    )
    assert [row.operation_id for row in rows_two] == ["dop_pg_1"]
    assert cursor_two is None

    filtered, _ = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status="SUCCEEDED",
        correlation_id=None,
        limit=10,
        cursor=None,
    )
    assert [row.operation_id for row in filtered] == ["dop_pg_2"]

    removed = repository.purge_expired_operations(ttl_seconds=1, now=now.replace(minute=2))
    assert removed == 2


def test_postgres_repository_list_operations_filters_and_invalid_cursor(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    now = datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc)
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_filter_1",
            operation_type="ANALYZE_SCENARIOS",
            status="FAILED",
            correlation_id="corr_op_pg_filter_1",
            created_at=now,
            started_at=None,
            finished_at=None,
            result_json=None,
            error_json={"code": "E1"},
            request_json={"scenarios": {"baseline": {"options": {}}}},
        )
    )
    repository.create_operation(
        DpmAsyncOperationRecord(
            operation_id="dop_pg_filter_2",
            operation_type="ANALYZE_SCENARIOS",
            status="SUCCEEDED",
            correlation_id="corr_op_pg_filter_2",
            created_at=now.replace(minute=1),
            started_at=now.replace(minute=1, second=1),
            finished_at=now.replace(minute=1, second=2),
            result_json={"ok": True},
            error_json=None,
            request_json=None,
        )
    )

    filtered, _ = repository.list_operations(
        created_from=now.replace(second=30),
        created_to=now.replace(minute=1, second=30),
        operation_type="ANALYZE_SCENARIOS",
        status="SUCCEEDED",
        correlation_id="corr_op_pg_filter_2",
        limit=10,
        cursor=None,
    )
    assert [row.operation_id for row in filtered] == ["dop_pg_filter_2"]

    invalid_cursor_rows, invalid_cursor = repository.list_operations(
        created_from=None,
        created_to=None,
        operation_type=None,
        status=None,
        correlation_id=None,
        limit=10,
        cursor="dop_pg_missing_cursor",
    )
    assert invalid_cursor_rows == []
    assert invalid_cursor is None


def test_postgres_repository_reports_unimplemented_for_other_methods(monkeypatch):
    repository, _ = _build_repository(monkeypatch)
    try:
        repository.list_runs  # type: ignore[attr-defined]
    except RuntimeError as exc:
        assert str(exc) == "DPM_SUPPORTABILITY_POSTGRES_NOT_IMPLEMENTED"
    else:
        raise AssertionError("Expected RuntimeError for unimplemented method access")


def test_postgres_json_dump_is_canonical():
    dumped = _json_dump({"b": 2, "a": 1})
    assert dumped == '{"a":1,"b":2}'


def test_postgres_connect_uses_imported_driver(monkeypatch):
    class _FakePsycopg:
        @staticmethod
        def connect(dsn, row_factory):
            return {"dsn": dsn, "row_factory": row_factory}

    monkeypatch.setattr(postgres_module, "_import_psycopg", lambda: (_FakePsycopg, "rf"))
    repository = object.__new__(PostgresDpmRunRepository)
    repository._dsn = "postgresql://user:pass@localhost:5432/dpm"
    connection = repository._connect()
    assert connection == {
        "dsn": "postgresql://user:pass@localhost:5432/dpm",
        "row_factory": "rf",
    }


def test_import_psycopg_helper(monkeypatch):
    fake_psycopg = ModuleType("psycopg")
    fake_rows = ModuleType("psycopg.rows")
    fake_rows.dict_row = object()
    fake_psycopg.rows = fake_rows

    monkeypatch.setitem(__import__("sys").modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(__import__("sys").modules, "psycopg.rows", fake_rows)

    psycopg_module, dict_row = _import_psycopg()
    assert psycopg_module is fake_psycopg
    assert dict_row is fake_rows.dict_row
