from src.core.workspace.session_models import WorkspaceSession
from src.infrastructure.workspace import (
    InMemoryWorkspaceSessionRepository,
)
from src.runtime.workspace_application import get_workspace_session_repository

WorkspaceSessionStore = InMemoryWorkspaceSessionRepository


def save_workspace_session(session: WorkspaceSession) -> None:
    get_workspace_session_repository().save(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return get_workspace_session_repository().get(workspace_id)


def reset_workspace_sessions() -> None:
    get_workspace_session_repository().reset()


def set_workspace_session_cache_size(max_size: int) -> None:
    get_workspace_session_repository().resize(max_size)
