from src.core.workspace.session_models import WorkspaceSession
from src.runtime.workspace_application import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE as _DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
)
from src.runtime.workspace_application import (
    get_workspace_session_repository,
    get_workspace_session_repository_class,
)

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = _DEFAULT_WORKSPACE_SESSION_CACHE_SIZE
WorkspaceSessionStore = get_workspace_session_repository_class()


def save_workspace_session(session: WorkspaceSession) -> None:
    get_workspace_session_repository().save(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return get_workspace_session_repository().get(workspace_id)


def reset_workspace_sessions() -> None:
    get_workspace_session_repository().reset()


def set_workspace_session_cache_size(max_size: int) -> None:
    get_workspace_session_repository().resize(max_size)
