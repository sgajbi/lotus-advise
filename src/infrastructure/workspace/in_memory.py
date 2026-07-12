from __future__ import annotations

from collections import OrderedDict
from typing import OrderedDict as OrderedDictType

from src.core.workspace.errors import WorkspaceNotFoundError
from src.core.workspace.session_models import WorkspaceSession
from src.infrastructure.workspace.session_cache_limits import (
    DEFAULT_WORKSPACE_SESSION_CACHE_SIZE,
    validate_workspace_session_cache_size,
)


class InMemoryWorkspaceSessionRepository:
    def __init__(self, *, max_size: int = DEFAULT_WORKSPACE_SESSION_CACHE_SIZE) -> None:
        self.max_size = validate_workspace_session_cache_size(max_size)
        self._sessions: OrderedDictType[str, WorkspaceSession] = OrderedDict()

    def save(self, session: WorkspaceSession) -> None:
        self._sessions[session.workspace_id] = session
        self._sessions.move_to_end(session.workspace_id)
        self._evict_over_capacity()

    def resize(self, max_size: int) -> None:
        self.max_size = validate_workspace_session_cache_size(max_size)
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
