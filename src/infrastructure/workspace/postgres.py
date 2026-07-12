from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
from importlib.util import find_spec
from typing import Any

from src.core.workspace.errors import WorkspaceNotFoundError
from src.core.workspace.session_models import WorkspaceSession
from src.infrastructure.postgres_migrations import apply_postgres_migrations
from src.infrastructure.workspace.postgres_records import (
    workspace_saved_version_values,
    workspace_session_from_rows,
    workspace_session_values,
)
from src.infrastructure.workspace.session_cache_limits import validate_workspace_session_cache_size

WorkspaceConnectionFactory = Callable[[], Any]


class PostgresWorkspaceSessionRepository:
    def __init__(
        self,
        *,
        dsn: str = "",
        connect: WorkspaceConnectionFactory | None = None,
        apply_migrations: bool = True,
    ) -> None:
        self._dsn = dsn
        self._connect_factory = connect or self._connect_from_dsn
        if connect is None:
            self._dsn = _validated_dsn(dsn)
        if apply_migrations:
            self._init_db()

    def save(self, session: WorkspaceSession) -> None:
        with closing(self._connect()) as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO advisory_workspace_sessions (
                        workspace_id, workspace_name, input_mode, created_by, created_at,
                        updated_at, retention_status, resolved_context_hash,
                        latest_evaluation_request_hash, lifecycle_proposal_id,
                        lifecycle_proposal_version_no, lifecycle_link_json, session_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (workspace_id) DO UPDATE SET
                        workspace_name = excluded.workspace_name,
                        input_mode = excluded.input_mode,
                        created_by = excluded.created_by,
                        created_at = excluded.created_at,
                        updated_at = excluded.updated_at,
                        retention_status = excluded.retention_status,
                        resolved_context_hash = excluded.resolved_context_hash,
                        latest_evaluation_request_hash = excluded.latest_evaluation_request_hash,
                        lifecycle_proposal_id = excluded.lifecycle_proposal_id,
                        lifecycle_proposal_version_no = excluded.lifecycle_proposal_version_no,
                        lifecycle_link_json = excluded.lifecycle_link_json,
                        session_json = excluded.session_json
                    """,
                    workspace_session_values(session),
                )
                connection.execute(
                    """
                    DELETE FROM advisory_workspace_saved_versions
                    WHERE workspace_id = %s
                    """,
                    (session.workspace_id,),
                )
                for saved_version in session.saved_versions:
                    connection.execute(
                        """
                        INSERT INTO advisory_workspace_saved_versions (
                            workspace_id, workspace_version_id, version_no, saved_by, saved_at,
                            draft_state_hash, evaluation_request_hash, replay_evidence_json,
                            saved_version_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        workspace_saved_version_values(
                            workspace_id=session.workspace_id,
                            saved_version=saved_version,
                        ),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def get(self, workspace_id: str) -> WorkspaceSession:
        with closing(self._connect()) as connection:
            session_row = connection.execute(
                """
                SELECT *
                FROM advisory_workspace_sessions
                WHERE workspace_id = %s
                """,
                (workspace_id,),
            ).fetchone()
            if session_row is None:
                raise WorkspaceNotFoundError("WORKSPACE_NOT_FOUND")
            saved_version_rows = connection.execute(
                """
                SELECT *
                FROM advisory_workspace_saved_versions
                WHERE workspace_id = %s
                ORDER BY version_no ASC, workspace_version_id ASC
                """,
                (workspace_id,),
            ).fetchall()
        return workspace_session_from_rows(
            session_row=session_row,
            saved_version_rows=list(saved_version_rows),
        )

    def reset(self) -> None:
        with closing(self._connect()) as connection:
            try:
                connection.execute("DELETE FROM advisory_workspace_idempotency")
                connection.execute("DELETE FROM advisory_workspace_events")
                connection.execute("DELETE FROM advisory_workspace_saved_versions")
                connection.execute("DELETE FROM advisory_workspace_sessions")
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def resize(self, max_size: int) -> None:
        validate_workspace_session_cache_size(max_size)

    def _connect(self) -> Any:
        return self._connect_factory()

    def _connect_from_dsn(self) -> Any:
        psycopg, dict_row = _import_psycopg()
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def _init_db(self) -> None:
        with closing(self._connect()) as connection:
            apply_postgres_migrations(connection=connection, namespace="workspace")


def _validated_dsn(dsn: str) -> str:
    if not dsn:
        raise RuntimeError("WORKSPACE_POSTGRES_DSN_REQUIRED")
    if find_spec("psycopg") is None:
        raise RuntimeError("WORKSPACE_POSTGRES_DRIVER_MISSING")
    return dsn


def _import_psycopg() -> tuple[Any, Any]:
    import psycopg
    from psycopg.rows import dict_row

    return psycopg, dict_row


__all__ = ["PostgresWorkspaceSessionRepository"]
