from src.core.workspace.models import (
    WorkspaceDraftState,
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
)


def build_workspace_session(
    *,
    request: WorkspaceSessionCreateRequest,
    workspace_id: str,
    created_at: str,
    draft_state: WorkspaceDraftState,
    resolved_context: WorkspaceResolvedContext,
) -> WorkspaceSession:
    return WorkspaceSession(
        workspace_id=workspace_id,
        workspace_name=request.workspace_name,
        lifecycle_state="ACTIVE",
        input_mode=request.input_mode,
        created_by=request.created_by,
        created_at=created_at,
        stateless_input=request.stateless_input,
        stateful_input=request.stateful_input,
        draft_state=draft_state,
        resolved_context=resolved_context,
        evaluation_summary=None,
        latest_proposal_result=None,
        latest_replay_evidence=None,
        saved_version_count=0,
        latest_saved_version=None,
        lifecycle_link=None,
        saved_versions=[],
    )
