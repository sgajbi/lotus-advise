from __future__ import annotations

from src.core.workspace.application import WorkspaceApplicationService
from src.core.workspace.ports import WorkspaceSessionRepository
from src.infrastructure.workspace import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
    InMemoryWorkspaceSessionRepository,
    LotusCoreWorkspaceSourceContextResolver,
)

_WORKSPACE_SESSION_REPOSITORY = InMemoryWorkspaceSessionRepository(
    max_size=DEFAULT_WORKSPACE_SESSION_CACHE_SIZE
)
_WORKSPACE_APPLICATION_SERVICE = WorkspaceApplicationService(
    session_repository=_WORKSPACE_SESSION_REPOSITORY,
    source_context_resolver=LotusCoreWorkspaceSourceContextResolver(),
)


def get_workspace_application_service() -> WorkspaceApplicationService:
    return _WORKSPACE_APPLICATION_SERVICE


def get_workspace_session_repository() -> WorkspaceSessionRepository:
    return _WORKSPACE_SESSION_REPOSITORY


def reset_workspace_application_for_tests() -> None:
    _WORKSPACE_SESSION_REPOSITORY.reset()
    _WORKSPACE_SESSION_REPOSITORY.resize(DEFAULT_WORKSPACE_SESSION_CACHE_SIZE)
