from __future__ import annotations

from src.api.services.workspace_context_resolution import build_initial_workspace_context
from src.core.workspace.models import WorkspaceSessionCreateRequest, WorkspaceSessionCreateResponse
from src.core.workspace.sessions import build_workspace_session


def build_workspace_session_create_response(
    *,
    request: WorkspaceSessionCreateRequest,
    workspace_id: str,
    created_at: str,
    fallback_as_of: str,
) -> WorkspaceSessionCreateResponse:
    resolved_context, draft_state = build_initial_workspace_context(
        request=request,
        fallback_as_of=fallback_as_of,
    )
    session = build_workspace_session(
        request=request,
        workspace_id=workspace_id,
        created_at=created_at,
        draft_state=draft_state,
        resolved_context=resolved_context,
    )
    return WorkspaceSessionCreateResponse(workspace=session)
