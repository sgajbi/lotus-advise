from __future__ import annotations

import pytest

import src.runtime.workspace_repositories as workspace_repositories
from src.core.workspace.session_models import WorkspaceSession
from src.infrastructure.workspace.in_memory import InMemoryWorkspaceSessionRepository
from src.runtime.workspace_application import (
    get_workspace_session_repository,
    reset_workspace_application_for_tests,
)


def test_workspace_runtime_requires_supported_backend(monkeypatch) -> None:
    monkeypatch.setenv("WORKSPACE_STORE_BACKEND", "unknown")

    with pytest.raises(RuntimeError, match="WORKSPACE_STORE_BACKEND_UNSUPPORTED"):
        workspace_repositories.workspace_store_backend_name()


def test_workspace_runtime_builds_postgres_repository_with_workspace_dsn(monkeypatch) -> None:
    captured: dict[str, str] = {}
    repository = InMemoryWorkspaceSessionRepository()

    def _factory(**kwargs):
        captured.update(kwargs)
        return repository

    monkeypatch.setenv("WORKSPACE_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgres://proposal")
    monkeypatch.setenv("WORKSPACE_POSTGRES_DSN", "postgres://workspace")
    monkeypatch.setattr(workspace_repositories, "PostgresWorkspaceSessionRepository", _factory)

    result = workspace_repositories.build_workspace_session_repository()

    assert result is repository
    assert captured == {"dsn": "postgres://workspace"}


def test_workspace_runtime_uses_proposal_dsn_fallback(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def _factory(**kwargs):
        captured.update(kwargs)
        return InMemoryWorkspaceSessionRepository()

    monkeypatch.setenv("WORKSPACE_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("PROPOSAL_POSTGRES_DSN", "postgres://proposal")
    monkeypatch.delenv("WORKSPACE_POSTGRES_DSN", raising=False)
    monkeypatch.setattr(workspace_repositories, "PostgresWorkspaceSessionRepository", _factory)

    workspace_repositories.build_workspace_session_repository()

    assert captured == {"dsn": "postgres://proposal"}


def test_workspace_runtime_fails_when_postgres_dsn_missing(monkeypatch) -> None:
    monkeypatch.setenv("WORKSPACE_STORE_BACKEND", "POSTGRES")
    monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
    monkeypatch.delenv("WORKSPACE_POSTGRES_DSN", raising=False)

    with pytest.raises(RuntimeError, match="WORKSPACE_POSTGRES_DSN_REQUIRED"):
        workspace_repositories.build_workspace_session_repository()


def test_workspace_runtime_reinitializes_repository_for_restart_proof(monkeypatch) -> None:
    first = InMemoryWorkspaceSessionRepository()
    second = InMemoryWorkspaceSessionRepository()
    repositories = iter([first, second])

    monkeypatch.setenv("WORKSPACE_STORE_BACKEND", "POSTGRES")
    monkeypatch.setenv("WORKSPACE_POSTGRES_DSN", "postgres://workspace")
    monkeypatch.setattr(
        workspace_repositories,
        "PostgresWorkspaceSessionRepository",
        lambda **_kwargs: next(repositories),
    )
    reset_workspace_application_for_tests()
    first_session = WorkspaceSession.model_construct(
        workspace_id="aws_restart_001",
        workspace_name="Restart proof",
    )

    get_workspace_session_repository().save(first_session)
    reset_workspace_application_for_tests()

    assert get_workspace_session_repository() is second

    reset_workspace_application_for_tests()
