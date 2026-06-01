from datetime import datetime, timezone

from src.api.services import workspace_saved_versions, workspace_store
from src.api.services.workspace_context_resolution import (
    build_initial_workspace_context,
    build_workspace_simulate_request,
)
from src.api.services.workspace_draft_actions import apply_workspace_draft_action_to_session
from src.api.services.workspace_lifecycle_handoff import execute_workspace_lifecycle_handoff
from src.api.services.workspace_reevaluations import reevaluate_workspace_session_state
from src.core.models import ProposalSimulateRequest
from src.core.proposals import ProposalWorkflowService
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.workspace.identifiers import new_workspace_id
from src.core.workspace.models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
    WorkspaceResumeRequest,
    WorkspaceSavedVersionListResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
)
from src.core.workspace.sessions import build_workspace_session

MAX_WORKSPACE_SESSION_CACHE_SIZE = workspace_store.DEFAULT_WORKSPACE_SESSION_CACHE_SIZE


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_business_date_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _build_simulate_request_for_workspace(session: WorkspaceSession) -> ProposalSimulateRequest:
    return build_workspace_simulate_request(session)


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    session = get_workspace_session(workspace_id)
    reevaluated_session = reevaluate_workspace_session_state(
        session=session,
        simulate_request_builder=_build_simulate_request_for_workspace,
    )
    _save_workspace_session(reevaluated_session)
    return reevaluated_session


def _save_workspace_session(session: WorkspaceSession) -> None:
    workspace_store.set_workspace_session_cache_size(MAX_WORKSPACE_SESSION_CACHE_SIZE)
    workspace_store.save_workspace_session(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return workspace_store.get_workspace_session(workspace_id)


def reset_workspace_sessions_for_tests() -> None:
    workspace_store.reset_workspace_sessions()


def create_workspace_session(
    request: WorkspaceSessionCreateRequest,
) -> WorkspaceSessionCreateResponse:
    resolved_context, draft_state = build_initial_workspace_context(
        request=request,
        fallback_as_of=_current_business_date_iso(),
    )

    session = build_workspace_session(
        request=request,
        workspace_id=new_workspace_id(),
        created_at=_utc_now_iso(),
        draft_state=draft_state,
        resolved_context=resolved_context,
    )
    _save_workspace_session(session)
    return WorkspaceSessionCreateResponse(workspace=session)


def apply_workspace_draft_action(
    workspace_id: str,
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    session = get_workspace_session(workspace_id)
    apply_workspace_draft_action_to_session(session=session, request=request)
    _save_workspace_session(session)
    updated_session = reevaluate_workspace_session(workspace_id)
    return WorkspaceDraftActionResponse(workspace=updated_session)


def save_workspace_version(
    workspace_id: str,
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    return workspace_saved_versions.save_workspace_version(
        workspace_id,
        request,
        saved_at=_utc_now_iso(),
    )


def list_workspace_saved_versions(
    workspace_id: str,
) -> WorkspaceSavedVersionListResponse:
    return workspace_saved_versions.list_workspace_saved_versions(workspace_id)


def get_workspace_saved_version_replay(
    workspace_id: str,
    workspace_version_id: str,
) -> AdvisoryReplayEvidenceResponse:
    return workspace_saved_versions.get_workspace_saved_version_replay(
        workspace_id,
        workspace_version_id,
    )


def resume_workspace_version(
    workspace_id: str,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    return workspace_saved_versions.resume_workspace_version(workspace_id, request)


def compare_workspace_to_saved_version(
    workspace_id: str,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    return workspace_saved_versions.compare_workspace_to_saved_version(workspace_id, request)


def handoff_workspace_to_proposal_lifecycle(
    workspace_id: str,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
) -> WorkspaceLifecycleHandoffResponse:
    session = get_workspace_session(workspace_id)
    response = execute_workspace_lifecycle_handoff(
        workspace_id=workspace_id,
        session=session,
        request=request,
        proposal_service=proposal_service,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        simulate_request_builder=_build_simulate_request_for_workspace,
        completed_at=_utc_now_iso(),
    )
    _save_workspace_session(session)
    return response
