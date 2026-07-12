from __future__ import annotations

import pytest

from src.core.workspace.draft_models import WorkspaceDraftState
from src.core.workspace.errors import WorkspaceNotFoundError
from src.core.workspace.session_models import WorkspaceSession
from src.core.workspace.version_models import (
    WorkspaceLifecycleLink,
    WorkspaceReplayEvidence,
    WorkspaceSavedVersion,
)
from src.core.workspace.versions import refresh_saved_version_metadata
from src.infrastructure.workspace.postgres import PostgresWorkspaceSessionRepository
from src.infrastructure.workspace.postgres_records import (
    workspace_saved_version_values,
    workspace_session_values,
)


class _Cursor:
    def __init__(self, *, row: dict | None = None, rows: list[dict] | None = None) -> None:
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return list(self._rows)


class _Connection:
    def __init__(
        self,
        *,
        session_row: dict | None = None,
        saved_version_rows: list[dict] | None = None,
        fail_statement: str | None = None,
    ) -> None:
        self.session_row = session_row
        self.saved_version_rows = saved_version_rows or []
        self.fail_statement = fail_statement
        self.executed: list[tuple[str, tuple | None]] = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def execute(self, query, args=None):
        sql = " ".join(str(query).split())
        self.executed.append((sql, args))
        if self.fail_statement and self.fail_statement in sql:
            raise RuntimeError("workspace persistence failed")
        if sql.startswith("SELECT * FROM advisory_workspace_sessions"):
            return _Cursor(row=self.session_row)
        if sql.startswith("SELECT * FROM advisory_workspace_saved_versions"):
            return _Cursor(rows=self.saved_version_rows)
        return _Cursor()

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def test_workspace_postgres_repository_saves_session_and_saved_versions() -> None:
    connection = _Connection()
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: connection,
        apply_migrations=False,
    )
    session = _workspace_session()

    repository.save(session)

    sql_statements = [sql for sql, _args in connection.executed]
    assert any("INSERT INTO advisory_workspace_sessions" in sql for sql in sql_statements)
    assert any("DELETE FROM advisory_workspace_saved_versions" in sql for sql in sql_statements)
    assert any("INSERT INTO advisory_workspace_saved_versions" in sql for sql in sql_statements)
    session_args = connection.executed[0][1]
    assert session_args is not None
    assert session_args[0] == "aws_pg_001"
    assert session_args[6] == "ACTIVE"
    assert session_args[8] == "sha256:evaluation_request"
    assert session_args[9] == "pp_workspace_001"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed is True


def test_workspace_postgres_repository_round_trips_session_with_saved_versions() -> None:
    session = _workspace_session()
    saved_version = session.saved_versions[0]
    connection = _Connection(
        session_row={"session_json": workspace_session_values(session)[-1]},
        saved_version_rows=[
            {
                "saved_version_json": workspace_saved_version_values(
                    workspace_id=session.workspace_id,
                    saved_version=saved_version,
                )[-1]
            }
        ],
    )
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: connection,
        apply_migrations=False,
    )

    loaded = repository.get(session.workspace_id)

    assert loaded.workspace_id == session.workspace_id
    assert loaded.saved_version_count == 1
    assert loaded.latest_saved_version is not None
    assert loaded.latest_saved_version.workspace_version_id == "awv_pg_001"
    assert loaded.saved_versions[0].replay_evidence.evaluation_request_hash == (
        "sha256:evaluation_request"
    )


def test_workspace_postgres_repository_missing_session_raises_domain_error() -> None:
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: _Connection(session_row=None),
        apply_migrations=False,
    )

    with pytest.raises(WorkspaceNotFoundError, match="WORKSPACE_NOT_FOUND"):
        repository.get("aws_missing")


def test_workspace_postgres_repository_rolls_back_on_partial_save_failure() -> None:
    connection = _Connection(fail_statement="DELETE FROM advisory_workspace_saved_versions")
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: connection,
        apply_migrations=False,
    )

    with pytest.raises(RuntimeError, match="workspace persistence failed"):
        repository.save(_workspace_session())

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed is True


def test_workspace_postgres_repository_rolls_back_saved_version_conflicts() -> None:
    connection = _Connection(fail_statement="INSERT INTO advisory_workspace_saved_versions")
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: connection,
        apply_migrations=False,
    )

    with pytest.raises(RuntimeError, match="workspace persistence failed"):
        repository.save(_workspace_session())

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert any(
        "INSERT INTO advisory_workspace_sessions" in sql for sql, _args in connection.executed
    )
    assert any(
        "INSERT INTO advisory_workspace_saved_versions" in sql for sql, _args in connection.executed
    )


def test_workspace_postgres_repository_reset_removes_child_tables_first() -> None:
    connection = _Connection()
    repository = PostgresWorkspaceSessionRepository(
        connect=lambda: connection,
        apply_migrations=False,
    )

    repository.reset()

    assert [sql for sql, _args in connection.executed] == [
        "DELETE FROM advisory_workspace_idempotency",
        "DELETE FROM advisory_workspace_events",
        "DELETE FROM advisory_workspace_saved_versions",
        "DELETE FROM advisory_workspace_sessions",
    ]
    assert connection.commits == 1


def _workspace_session() -> WorkspaceSession:
    replay_evidence = WorkspaceReplayEvidence(
        input_mode="stateful",
        resolved_context={
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "as_of": "2026-07-11",
            "portfolio_snapshot_id": "ps_pg_001",
        },
        draft_state_hash="sha256:draft_state",
        evaluation_request_hash="sha256:evaluation_request",
        captured_at="2026-07-11T09:00:00+00:00",
    )
    session = WorkspaceSession(
        workspace_id="aws_pg_001",
        workspace_name="Postgres workspace",
        lifecycle_state="ACTIVE",
        input_mode="stateful",
        created_by="advisor_123",
        created_at="2026-07-11T08:30:00+00:00",
        stateful_input={
            "portfolio_id": "PB_SG_GLOBAL_BAL_001",
            "as_of": "2026-07-11",
        },
        draft_state=WorkspaceDraftState(),
        resolved_context=replay_evidence.resolved_context,
        latest_replay_evidence=replay_evidence,
        lifecycle_link=WorkspaceLifecycleLink(
            proposal_id="pp_workspace_001",
            current_version_no=2,
            last_handoff_at="2026-07-11T09:05:00+00:00",
            last_handoff_by="advisor_123",
        ),
    )
    session.saved_versions.append(
        WorkspaceSavedVersion(
            workspace_version_id="awv_pg_001",
            version_number=1,
            version_label="Initial saved draft",
            saved_by="advisor_123",
            saved_at="2026-07-11T08:45:00+00:00",
            draft_state=WorkspaceDraftState(),
            replay_evidence=replay_evidence,
        )
    )
    refresh_saved_version_metadata(session)
    return session
