from datetime import datetime, timezone
from types import ModuleType

import src.infrastructure.dpm_runs.postgres as postgres_module
from src.core.dpm_runs.models import DpmRunRecord
from src.infrastructure.dpm_runs.postgres import (
    PostgresDpmRunRepository,
    _import_psycopg,
    _json_dump,
)


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeConnection:
    def __init__(self):
        self.runs = {}
        self.artifacts = {}
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
