from pathlib import Path

import pytest

import src.infrastructure.postgres_migrations as migrations_module
from src.infrastructure.postgres_migrations import PostgresMigration, apply_postgres_migrations


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self):
        self.schema_migrations: dict[tuple[str, str], str] = {}
        self.applied_statements: list[str] = []
        self.commit_count = 0

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        if sql.startswith("CREATE TABLE IF NOT EXISTS schema_migrations"):
            return _FakeCursor()
        if "FROM schema_migrations" in sql:
            namespace = args[0]
            rows = [
                {"version": version, "checksum": checksum}
                for (stored_namespace, version), checksum in self.schema_migrations.items()
                if stored_namespace == namespace
            ]
            return _FakeCursor(rows=sorted(rows, key=lambda row: row["version"]))
        if "INSERT INTO schema_migrations" in sql:
            self.schema_migrations[(args[1], args[0])] = args[2]
            return _FakeCursor()
        self.applied_statements.append(sql)
        return _FakeCursor()

    def commit(self):
        self.commit_count += 1


def test_apply_postgres_migrations_is_forward_only_and_idempotent():
    connection = _FakeConnection()

    apply_postgres_migrations(connection=connection, namespace="dpm")
    first_count = len(connection.applied_statements)
    assert first_count > 0
    assert ("dpm", "0001") in connection.schema_migrations
    assert connection.commit_count == 1

    apply_postgres_migrations(connection=connection, namespace="dpm")
    assert len(connection.applied_statements) == first_count
    assert connection.commit_count == 2


def test_apply_postgres_migrations_detects_checksum_mismatch(monkeypatch, tmp_path: Path):
    sql_path = tmp_path / "0001_test.sql"
    sql_path.write_text("CREATE TABLE IF NOT EXISTS sample_table (id TEXT PRIMARY KEY);")
    migration = PostgresMigration(version="0001", sql_path=sql_path, checksum="checksum-new")
    monkeypatch.setattr(migrations_module, "_load_migrations", lambda namespace: [migration])

    connection = _FakeConnection()
    connection.schema_migrations[("custom", "0001")] = "checksum-old"

    with pytest.raises(RuntimeError) as exc:
        apply_postgres_migrations(connection=connection, namespace="custom")
    assert str(exc.value) == "POSTGRES_MIGRATION_CHECKSUM_MISMATCH:custom:0001"
