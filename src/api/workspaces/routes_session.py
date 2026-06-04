from typing import cast

from fastapi import APIRouter, status

from src.api.services.workspace_service import (
    apply_workspace_draft_action,
    compare_workspace_to_saved_version,
    create_workspace_session,
    get_workspace_saved_version_replay,
    get_workspace_session,
    list_workspace_saved_versions,
    reevaluate_workspace_session,
    resume_workspace_version,
    save_workspace_version,
)
from src.api.workspaces.errors import run_workspace_operation
from src.api.workspaces.parameters import (
    WorkspaceCreateCorrelationIdHeader,
    WorkspaceIdPath,
    WorkspaceVersionIdPath,
)
from src.api.workspaces.response_metadata import (
    WORKSPACE_COMPARE_RESPONSES,
    WORKSPACE_CREATE_RESPONSES,
    WORKSPACE_DRAFT_ACTION_RESPONSES,
    WORKSPACE_EVALUATE_RESPONSES,
    WORKSPACE_NOT_FOUND_RESPONSE,
    WORKSPACE_RESUME_RESPONSES,
    WORKSPACE_SAVE_RESPONSES,
    WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.workspace.action_models import (
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
)
from src.core.workspace.compare_models import (
    WorkspaceCompareRequest,
    WorkspaceCompareResponse,
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

router = APIRouter()


def _resolve_workspace_or_404(workspace_id: str) -> WorkspaceSession:
    return cast(
        WorkspaceSession,
        run_workspace_operation(lambda: get_workspace_session(workspace_id)),
    )


@router.post(
    "/advisory/workspaces",
    response_model=WorkspaceSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Advisory Workspace"],
    summary="Create an Advisory Workspace Session",
    description=(
        "Creates an advisory workspace session for iterative proposal drafting. "
        "The workspace contract supports both `stateless` and `stateful` operating modes and "
        "returns an initial resolved advisory context for replay and audit."
    ),
    responses=WORKSPACE_CREATE_RESPONSES,
)
def create_workspace(
    request: WorkspaceSessionCreateRequest,
    correlation_id: WorkspaceCreateCorrelationIdHeader = None,
) -> WorkspaceSessionCreateResponse:
    _ = correlation_id
    return create_workspace_session(request)


@router.get(
    "/advisory/workspaces/{workspace_id}",
    response_model=WorkspaceSession,
    tags=["Advisory Workspace"],
    summary="Get an Advisory Workspace Session",
    description=(
        "Returns the current advisory workspace session, including draft state and latest "
        "evaluation."
    ),
    responses=WORKSPACE_NOT_FOUND_RESPONSE,
)
def get_workspace(
    workspace_id: WorkspaceIdPath,
) -> WorkspaceSession:
    return _resolve_workspace_or_404(workspace_id)


@router.post(
    "/advisory/workspaces/{workspace_id}/draft-actions",
    response_model=WorkspaceDraftActionResponse,
    tags=["Advisory Workspace"],
    summary="Apply an Advisory Workspace Draft Action",
    description=(
        "Applies one deterministic draft action to the advisory workspace and re-evaluates the "
        "workspace immediately when evaluation context is available."
    ),
    responses=WORKSPACE_DRAFT_ACTION_RESPONSES,
)
def apply_draft_action(
    workspace_id: WorkspaceIdPath,
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    return cast(
        WorkspaceDraftActionResponse,
        run_workspace_operation(lambda: apply_workspace_draft_action(workspace_id, request)),
    )


@router.post(
    "/advisory/workspaces/{workspace_id}/evaluate",
    response_model=WorkspaceSession,
    tags=["Advisory Workspace"],
    summary="Re-evaluate an Advisory Workspace Session",
    description=(
        "Runs deterministic re-evaluation for the current workspace draft and returns the updated "
        "workspace session with normalized evaluation outputs."
    ),
    responses=WORKSPACE_EVALUATE_RESPONSES,
)
def evaluate_workspace(
    workspace_id: WorkspaceIdPath,
) -> WorkspaceSession:
    return cast(
        WorkspaceSession,
        run_workspace_operation(lambda: reevaluate_workspace_session(workspace_id)),
    )


@router.post(
    "/advisory/workspaces/{workspace_id}/save",
    response_model=WorkspaceSaveResponse,
    tags=["Advisory Workspace"],
    summary="Save an Advisory Workspace Version",
    description=(
        "Captures the current advisory workspace draft as a saved version with replay-safe "
        "evidence for resume and compare workflows."
    ),
    responses=WORKSPACE_SAVE_RESPONSES,
)
def save_workspace(
    workspace_id: WorkspaceIdPath,
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    return cast(
        WorkspaceSaveResponse,
        run_workspace_operation(lambda: save_workspace_version(workspace_id, request)),
    )


@router.get(
    "/advisory/workspaces/{workspace_id}/saved-versions",
    response_model=WorkspaceSavedVersionListResponse,
    tags=["Advisory Workspace"],
    summary="List Saved Advisory Workspace Versions",
    description=(
        "Returns saved advisory workspace versions available for support, compare, and resume "
        "workflows."
    ),
    responses=WORKSPACE_NOT_FOUND_RESPONSE,
)
def list_saved_workspace_versions(
    workspace_id: WorkspaceIdPath,
) -> WorkspaceSavedVersionListResponse:
    return cast(
        WorkspaceSavedVersionListResponse,
        run_workspace_operation(lambda: list_workspace_saved_versions(workspace_id)),
    )


@router.get(
    "/advisory/workspaces/{workspace_id}/saved-versions/{workspace_version_id}/replay-evidence",
    response_model=AdvisoryReplayEvidenceResponse,
    tags=["Advisory Operations & Support"],
    summary="Get Saved Workspace Replay Evidence",
    description=(
        "Returns normalized replay evidence for a saved workspace version so support and audit "
        "users can trace workspace evidence continuity into lifecycle flows."
    ),
    responses=WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE,
)
def get_saved_workspace_version_replay_evidence(
    workspace_id: WorkspaceIdPath,
    workspace_version_id: WorkspaceVersionIdPath,
) -> AdvisoryReplayEvidenceResponse:
    return cast(
        AdvisoryReplayEvidenceResponse,
        run_workspace_operation(
            lambda: get_workspace_saved_version_replay(workspace_id, workspace_version_id)
        ),
    )


@router.post(
    "/advisory/workspaces/{workspace_id}/resume",
    response_model=WorkspaceSession,
    tags=["Advisory Workspace"],
    summary="Resume a Saved Advisory Workspace Version",
    description=(
        "Restores a saved advisory workspace version into the current editable draft session."
    ),
    responses=WORKSPACE_RESUME_RESPONSES,
)
def resume_workspace(
    workspace_id: WorkspaceIdPath,
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    return cast(
        WorkspaceSession,
        run_workspace_operation(lambda: resume_workspace_version(workspace_id, request)),
    )


@router.post(
    "/advisory/workspaces/{workspace_id}/compare",
    response_model=WorkspaceCompareResponse,
    tags=["Advisory Workspace"],
    summary="Compare Current Workspace Draft to a Saved Version",
    description=(
        "Returns a deterministic comparison between the current advisory workspace draft and a "
        "saved workspace version baseline."
    ),
    responses=WORKSPACE_COMPARE_RESPONSES,
)
def compare_workspace(
    workspace_id: WorkspaceIdPath,
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    return cast(
        WorkspaceCompareResponse,
        run_workspace_operation(lambda: compare_workspace_to_saved_version(workspace_id, request)),
    )
