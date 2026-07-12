from typing import cast

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals import ProposalWorkflowService
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.workspace.action_models import (
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
)
from src.core.workspace.application import WorkspaceApplicationService
from src.core.workspace.compare_models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
)
from src.core.workspace.handoff_models import (
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
)
from src.core.workspace.save_models import (
    WorkspaceResumeRequest,
    WorkspaceSavedVersionListResponse,
    WorkspaceSaveRequest,
    WorkspaceSaveResponse,
)
from src.core.workspace.session_models import (
    WorkspaceSession,
    WorkspaceSessionCreateRequest,
    WorkspaceSessionCreateResponse,
)
from src.runtime.workspace_application import (
    get_workspace_application_service,
    get_workspace_session_repository,
)

MAX_WORKSPACE_SESSION_CACHE_SIZE = 500


def _workspace_application() -> WorkspaceApplicationService:
    get_workspace_session_repository().resize(MAX_WORKSPACE_SESSION_CACHE_SIZE)
    return get_workspace_application_service()


def _build_simulate_request_for_workspace(session: WorkspaceSession) -> ProposalSimulateRequest:
    return _workspace_application().build_simulate_request_for_workspace(session)


def reevaluate_workspace_session(workspace_id: str) -> WorkspaceSession:
    return _workspace_application().reevaluate_session(workspace_id)


def _save_workspace_session(session: WorkspaceSession) -> None:
    _workspace_application().save_session(session)


def get_workspace_session(workspace_id: str) -> WorkspaceSession:
    return _workspace_application().get_session(workspace_id)


def reset_workspace_sessions_for_tests() -> None:
    _workspace_application().reset_sessions_for_tests()


def create_workspace_session(
    request: WorkspaceSessionCreateRequest,
) -> WorkspaceSessionCreateResponse:
    return _workspace_application().create_session(request)


def apply_workspace_draft_action(
    workspace_id: str,
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    return _workspace_application().apply_draft_action(workspace_id, request)


def save_workspace_version(
    workspace_id: str,
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    return _workspace_application().save_version(workspace_id, request)


def list_workspace_saved_versions(
    workspace_id: str,
) -> WorkspaceSavedVersionListResponse:
    return _workspace_application().list_saved_versions(workspace_id)


def get_workspace_saved_version_replay(
    workspace_id: str,
    workspace_version_id: str,
) -> AdvisoryReplayEvidenceResponse:
    return _workspace_application().get_saved_version_replay(workspace_id, workspace_version_id)


def resume_workspace_version(
    workspace_id: str,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    return _workspace_application().resume_version(workspace_id, request)


def compare_workspace_to_saved_version(
    workspace_id: str,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    return _workspace_application().compare_to_saved_version(workspace_id, request)


def handoff_workspace_to_proposal_lifecycle(
    workspace_id: str,
    request: WorkspaceLifecycleHandoffRequest,
    proposal_service: ProposalWorkflowService,
    idempotency_key: str | None,
    correlation_id: str | None,
) -> WorkspaceLifecycleHandoffResponse:
    response = _workspace_application().handoff_to_proposal_lifecycle(
        workspace_id=workspace_id,
        request=request,
        proposal_lifecycle=proposal_service,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    return cast(WorkspaceLifecycleHandoffResponse, response)
