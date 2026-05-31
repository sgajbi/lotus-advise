import pytest

from src.api.services.workspace_store import WorkspaceNotFoundError, WorkspaceSessionStore
from src.core.workspace.models import WorkspaceSession


def _workspace_session(*, workspace_id: str, workspace_name: str) -> WorkspaceSession:
    return WorkspaceSession.model_construct(
        workspace_id=workspace_id,
        workspace_name=workspace_name,
    )


def test_workspace_session_store_evicts_oldest_session() -> None:
    store = WorkspaceSessionStore(max_size=1)
    store.save(_workspace_session(workspace_id="ws_first", workspace_name="First workspace"))
    store.save(_workspace_session(workspace_id="ws_second", workspace_name="Second workspace"))

    with pytest.raises(WorkspaceNotFoundError, match="WORKSPACE_NOT_FOUND"):
        store.get("ws_first")

    assert store.get("ws_second").workspace_name == "Second workspace"


def test_workspace_session_store_reset_clears_sessions() -> None:
    store = WorkspaceSessionStore(max_size=2)
    store.save(_workspace_session(workspace_id="ws_001", workspace_name="Workspace"))

    store.reset()

    with pytest.raises(WorkspaceNotFoundError, match="WORKSPACE_NOT_FOUND"):
        store.get("ws_001")


@pytest.mark.parametrize("max_size", [0, -1, True])
def test_workspace_session_store_rejects_invalid_cache_size(max_size: int) -> None:
    with pytest.raises(ValueError, match="WORKSPACE_SESSION_CACHE_SIZE_INVALID"):
        WorkspaceSessionStore(max_size=max_size)


def test_workspace_session_store_resize_evicts_oldest_sessions_immediately() -> None:
    store = WorkspaceSessionStore(max_size=3)
    store.save(_workspace_session(workspace_id="ws_first", workspace_name="First workspace"))
    store.save(_workspace_session(workspace_id="ws_second", workspace_name="Second workspace"))
    store.save(_workspace_session(workspace_id="ws_third", workspace_name="Third workspace"))

    store.resize(1)

    with pytest.raises(WorkspaceNotFoundError, match="WORKSPACE_NOT_FOUND"):
        store.get("ws_first")
    with pytest.raises(WorkspaceNotFoundError, match="WORKSPACE_NOT_FOUND"):
        store.get("ws_second")

    assert store.get("ws_third").workspace_name == "Third workspace"

    with pytest.raises(ValueError, match="WORKSPACE_SESSION_CACHE_SIZE_INVALID"):
        store.resize(0)
