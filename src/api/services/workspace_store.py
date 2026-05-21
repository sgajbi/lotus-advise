from collections import OrderedDict
from typing import OrderedDict as OrderedDictType

from src.core.workspace.models import WorkspaceSession

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = 500


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceSessionStore:
    def __init__(self, *, max_size: int = DEFAULT_WORKSPACE_SESSION_CACHE_SIZE) -> None:
        self.max_size = max_size
        self._sessions: OrderedDictType[str, WorkspaceSession] = OrderedDict()

    def save(self, session: WorkspaceSession) -> None:
        self._sessions[session.workspace_id] = session
        self._sessions.move_to_end(session.workspace_id)
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
    WORKSPACE_SESSION_STORE.max_size = max_size
