from __future__ import annotations

import importlib
from typing import Any, cast

from src.core.workspace.application import WorkspaceApplicationService
from src.core.workspace.ports import (
    WorkspaceSessionRepository,
    WorkspaceSourceContextResolver,
)
from src.runtime.workspace_repositories import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
    build_workspace_session_repository,
)


def _workspace_infrastructure_module() -> Any:
    return importlib.import_module("src.infrastructure.workspace")


def get_workspace_session_repository_class() -> type[Any]:
    return cast(
        type[Any],
        _workspace_infrastructure_module().InMemoryWorkspaceSessionRepository,
    )


def _build_workspace_source_context_resolver() -> WorkspaceSourceContextResolver:
    resolver_class = _workspace_infrastructure_module().LotusCoreWorkspaceSourceContextResolver
    return cast(WorkspaceSourceContextResolver, resolver_class())


_WORKSPACE_SESSION_REPOSITORY: WorkspaceSessionRepository | None = None
_WORKSPACE_SOURCE_CONTEXT_RESOLVER: WorkspaceSourceContextResolver | None = None
_WORKSPACE_APPLICATION_SERVICE: WorkspaceApplicationService | None = None


def _ensure_workspace_runtime() -> None:
    global _WORKSPACE_APPLICATION_SERVICE
    global _WORKSPACE_SESSION_REPOSITORY
    global _WORKSPACE_SOURCE_CONTEXT_RESOLVER
    if _WORKSPACE_APPLICATION_SERVICE is not None:
        return
    _WORKSPACE_SESSION_REPOSITORY = build_workspace_session_repository()
    _WORKSPACE_SOURCE_CONTEXT_RESOLVER = _build_workspace_source_context_resolver()
    _WORKSPACE_APPLICATION_SERVICE = WorkspaceApplicationService(
        session_repository=_WORKSPACE_SESSION_REPOSITORY,
        source_context_resolver=_WORKSPACE_SOURCE_CONTEXT_RESOLVER,
    )


def get_workspace_application_service() -> WorkspaceApplicationService:
    _ensure_workspace_runtime()
    return cast(WorkspaceApplicationService, _WORKSPACE_APPLICATION_SERVICE)


def get_workspace_session_repository() -> WorkspaceSessionRepository:
    _ensure_workspace_runtime()
    return cast(WorkspaceSessionRepository, _WORKSPACE_SESSION_REPOSITORY)


def get_workspace_source_context_resolver() -> WorkspaceSourceContextResolver:
    _ensure_workspace_runtime()
    return cast(WorkspaceSourceContextResolver, _WORKSPACE_SOURCE_CONTEXT_RESOLVER)


def reset_workspace_application_for_tests() -> None:
    global _WORKSPACE_APPLICATION_SERVICE
    global _WORKSPACE_SESSION_REPOSITORY
    global _WORKSPACE_SOURCE_CONTEXT_RESOLVER
    if _WORKSPACE_SESSION_REPOSITORY is not None:
        _WORKSPACE_SESSION_REPOSITORY.reset()
        _WORKSPACE_SESSION_REPOSITORY.resize(DEFAULT_WORKSPACE_SESSION_CACHE_SIZE)
    _WORKSPACE_APPLICATION_SERVICE = None
    _WORKSPACE_SESSION_REPOSITORY = None
    _WORKSPACE_SOURCE_CONTEXT_RESOLVER = None
