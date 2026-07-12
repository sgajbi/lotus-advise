from __future__ import annotations

import importlib
import os
from typing import Callable, cast

from src.core.workspace.ports import WorkspaceSessionRepository
from src.runtime.proposal_repositories import (
    _postgres_connection_exception_types,
    proposal_postgres_dsn,
)

WorkspaceSessionRepositoryFactory = Callable[..., WorkspaceSessionRepository]

PostgresWorkspaceSessionRepository: WorkspaceSessionRepositoryFactory | None = None

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = 500


def workspace_store_backend_name() -> str:
    backend = os.getenv("WORKSPACE_STORE_BACKEND", "POSTGRES").strip().upper()
    if backend not in {"POSTGRES", "IN_MEMORY"}:
        raise RuntimeError("WORKSPACE_STORE_BACKEND_UNSUPPORTED")
    return backend


def workspace_postgres_dsn() -> str:
    return os.getenv("WORKSPACE_POSTGRES_DSN", "").strip() or proposal_postgres_dsn()


def workspace_configured_postgres_dsn() -> str:
    return os.getenv("WORKSPACE_POSTGRES_DSN", "").strip()


def build_workspace_session_repository() -> WorkspaceSessionRepository:
    backend = workspace_store_backend_name()
    if backend == "IN_MEMORY":
        return _in_memory_workspace_session_repository_factory()(
            max_size=DEFAULT_WORKSPACE_SESSION_CACHE_SIZE
        )
    dsn = workspace_postgres_dsn()
    if not dsn:
        raise RuntimeError("WORKSPACE_POSTGRES_DSN_REQUIRED")
    try:
        return cast(WorkspaceSessionRepository, _postgres_workspace_repository_factory()(dsn=dsn))
    except RuntimeError:
        raise
    except _postgres_connection_exception_types() as exc:
        raise RuntimeError("WORKSPACE_POSTGRES_CONNECTION_FAILED") from exc


def _postgres_workspace_repository_factory() -> WorkspaceSessionRepositoryFactory:
    if PostgresWorkspaceSessionRepository is not None:
        return PostgresWorkspaceSessionRepository
    module = importlib.import_module("src.infrastructure.workspace")
    return cast(WorkspaceSessionRepositoryFactory, module.PostgresWorkspaceSessionRepository)


def _in_memory_workspace_session_repository_factory() -> WorkspaceSessionRepositoryFactory:
    module = importlib.import_module("src.infrastructure.workspace")
    return cast(WorkspaceSessionRepositoryFactory, module.InMemoryWorkspaceSessionRepository)


__all__ = [
    "DEFAULT_WORKSPACE_SESSION_CACHE_SIZE",
    "PostgresWorkspaceSessionRepository",
    "build_workspace_session_repository",
    "workspace_configured_postgres_dsn",
    "workspace_postgres_dsn",
    "workspace_store_backend_name",
]
