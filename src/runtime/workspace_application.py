from __future__ import annotations

import importlib
from typing import Any, cast

from src.core.workspace.application import WorkspaceApplicationService
from src.core.workspace.ports import (
    WorkspaceSessionRepository,
    WorkspaceSourceContextResolver,
)

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = 500


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


_WORKSPACE_SESSION_REPOSITORY = cast(
    WorkspaceSessionRepository,
    get_workspace_session_repository_class()(
        max_size=DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
    ),
)
_WORKSPACE_SOURCE_CONTEXT_RESOLVER = _build_workspace_source_context_resolver()
_WORKSPACE_APPLICATION_SERVICE = WorkspaceApplicationService(
    session_repository=_WORKSPACE_SESSION_REPOSITORY,
    source_context_resolver=_WORKSPACE_SOURCE_CONTEXT_RESOLVER,
)


def get_workspace_application_service() -> WorkspaceApplicationService:
    return _WORKSPACE_APPLICATION_SERVICE


def get_workspace_session_repository() -> WorkspaceSessionRepository:
    return _WORKSPACE_SESSION_REPOSITORY


def get_workspace_source_context_resolver() -> WorkspaceSourceContextResolver:
    return _WORKSPACE_SOURCE_CONTEXT_RESOLVER


def reset_workspace_application_for_tests() -> None:
    _WORKSPACE_SESSION_REPOSITORY.reset()
    _WORKSPACE_SESSION_REPOSITORY.resize(DEFAULT_WORKSPACE_SESSION_CACHE_SIZE)
