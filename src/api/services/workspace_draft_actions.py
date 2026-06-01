from __future__ import annotations

from src.api.services.workspace_errors import (
    WORKSPACE_DRAFT_ACTION_INVALID_DETAIL,
    WorkspaceNotFoundError,
    safe_workspace_error_detail,
)
from src.core.workspace.draft_actions import (
    WorkspaceDraftActionError,
    apply_workspace_draft_action_to_state,
)
from src.core.workspace.models import WorkspaceDraftActionRequest, WorkspaceSession


def apply_workspace_draft_action_to_session(
    *,
    session: WorkspaceSession,
    request: WorkspaceDraftActionRequest,
) -> None:
    try:
        apply_workspace_draft_action_to_state(
            draft_state=session.draft_state,
            request=request,
        )
    except WorkspaceDraftActionError as exc:
        raise WorkspaceNotFoundError(
            safe_workspace_error_detail(
                str(exc),
                fallback=WORKSPACE_DRAFT_ACTION_INVALID_DETAIL,
            )
        ) from exc
