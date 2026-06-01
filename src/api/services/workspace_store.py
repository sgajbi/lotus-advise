from collections import OrderedDict
from typing import OrderedDict as OrderedDictType

from src.api.services.workspace_errors import WorkspaceNotFoundError
from src.core.workspace.models import WorkspaceSession

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = 500


def _validate_workspace_session_cache_size(max_size: int) -> int:
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 1:
        raise ValueError("WORKSPACE_SESSION_CACHE_SIZE_INVALID")
    return max_size


class WorkspaceSessionStore:
    def __init__(self, *, max_size: int = DEFAULT_WORKSPACE_SESSION_CACHE_SIZE) -> None:
        self.max_size = _validate_workspace_session_cache_size(max_size)
        self._sessions: OrderedDictType[str, WorkspaceSession] = OrderedDict()

    def save(self, session: WorkspaceSession) -> None:
        self._sessions[session.workspace_id] = session
        self._sessions.move_to_end(session.workspace_id)
        self._evict_over_capacity()

    def resize(self, max_size: int) -> None:
        self.max_size = _validate_workspace_session_cache_size(max_size)
        self._evict_over_capacity()

    def _evict_over_capacity(self) -> None:
        while len(self._sessions) > self.max_size:
            self._sessions.popitem(last=False)

    def get(self, workspace_id: str) -> WorkspaceSession:
        session = self._sessions.get(workspace_id)
        if session is None:
            raise WorkspaceNotFoundError("WORKSPACE_NOT_FOUND")
        return session

    def reset(self) -> None:
        self._sessions.clear()


WORKSPACE_SESSION_STORE = WorkspaceSessionStore()


def save_workspace_session(session: WorkspaceSession) -> None:
    WORKSPACE_SESSION_STORE.save(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return WORKSPACE_SESSION_STORE.get(workspace_id)


def reset_workspace_sessions() -> None:
    WORKSPACE_SESSION_STORE.reset()


def set_workspace_session_cache_size(max_size: int) -> None:
    WORKSPACE_SESSION_STORE.resize(max_size)
