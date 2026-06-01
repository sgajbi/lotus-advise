from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Path, status

import src.api.proposals.router as proposal_shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.api.services.workspace_ai_service import (
    WorkspaceAssistantUnavailableError,
    apply_workspace_rationale_review_action,
    generate_workspace_rationale,
)
from src.api.services.workspace_service import (
    WorkspaceEvaluationUnavailableError,
    WorkspaceLifecycleHandoffUnavailableError,
    WorkspaceNotFoundError,
    WorkspaceSavedVersionNotFoundError,
    apply_workspace_draft_action,
    compare_workspace_to_saved_version,
    create_workspace_session,
    get_workspace_saved_version_replay,
    get_workspace_session,
    handoff_workspace_to_proposal_lifecycle,
    list_workspace_saved_versions,
    reevaluate_workspace_session,
    resume_workspace_version,
    save_workspace_version,
)
from src.api.workspaces.errors import (
    workspace_assistant_unavailable_exception,
    workspace_conflict_exception,
    workspace_not_found_exception,
)
from src.api.workspaces.response_metadata import (
    WORKSPACE_COMPARE_RESPONSES,
    WORKSPACE_CREATE_RESPONSES,
    WORKSPACE_DRAFT_ACTION_RESPONSES,
    WORKSPACE_EVALUATE_RESPONSES,
    WORKSPACE_HANDOFF_RESPONSES,
    WORKSPACE_NOT_FOUND_RESPONSE,
    WORKSPACE_RATIONALE_RESPONSES,
    WORKSPACE_RATIONALE_REVIEW_RESPONSES,
    WORKSPACE_RESUME_RESPONSES,
    WORKSPACE_SAVE_RESPONSES,
    WORKSPACE_SAVED_VERSION_NOT_FOUND_RESPONSE,
)
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.workspace.models import (
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
    WorkspaceAssistantWorkflowPackRunReviewActionRequest,
    WorkspaceAssistantWorkflowPackRunReviewActionResponse,
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

router = APIRouter()


def _resolve_workspace_or_404(workspace_id: str) -> WorkspaceSession:
    try:
        return get_workspace_session(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


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
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description=(
                "Optional trace and correlation identifier propagated through the advisory "
                "workflow."
            ),
            examples=["corr-workspace-1234"],
        ),
    ] = None,
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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceDraftActionRequest,
) -> WorkspaceDraftActionResponse:
    try:
        return apply_workspace_draft_action(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceEvaluationUnavailableError as exc:
        raise workspace_conflict_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
) -> WorkspaceSession:
    try:
        return reevaluate_workspace_session(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceEvaluationUnavailableError as exc:
        raise workspace_conflict_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceSaveRequest,
) -> WorkspaceSaveResponse:
    try:
        return save_workspace_version(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
) -> WorkspaceSavedVersionListResponse:
    try:
        return list_workspace_saved_versions(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    workspace_version_id: Annotated[
        str,
        Path(description="Saved workspace version identifier.", examples=["awv_001"]),
    ],
) -> AdvisoryReplayEvidenceResponse:
    try:
        return get_workspace_saved_version_replay(workspace_id, workspace_version_id)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceSavedVersionNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceResumeRequest,
) -> WorkspaceSession:
    try:
        return resume_workspace_version(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceSavedVersionNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


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
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceCompareRequest,
) -> WorkspaceCompareResponse:
    try:
        return compare_workspace_to_saved_version(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceSavedVersionNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/assistant/rationale",
    response_model=WorkspaceAssistantResponse,
    tags=["Advisory Workspace"],
    summary="Generate an Advisory Workspace Rationale",
    description=(
        "Builds an evidence-grounded workspace rationale through the Lotus AI boundary using the "
        "current evaluated workspace state. The returned output always includes the deterministic "
        "evidence bundle that was supplied to the AI workflow."
    ),
    responses=WORKSPACE_RATIONALE_RESPONSES,
)
def generate_workspace_rationale_endpoint(
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceAssistantRequest,
) -> WorkspaceAssistantResponse:
    try:
        return generate_workspace_rationale(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceAssistantUnavailableError as exc:
        raise workspace_assistant_unavailable_exception(exc) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/assistant/rationale/review-actions",
    response_model=WorkspaceAssistantWorkflowPackRunReviewActionResponse,
    tags=["Advisory Workspace"],
    summary="Apply an Advisory Workspace Rationale Review Action",
    description=(
        "Applies a bounded workflow-pack review action for the Lotus AI run backing an advisory "
        "workspace rationale. Lotus AI remains the run-ledger authority, and this route preserves "
        "returned replacement lineage and supportability posture without rewriting the rationale "
        "narrative."
    ),
    responses=WORKSPACE_RATIONALE_REVIEW_RESPONSES,
)
def apply_workspace_rationale_review_action_endpoint(
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> WorkspaceAssistantWorkflowPackRunReviewActionResponse:
    try:
        return apply_workspace_rationale_review_action(workspace_id, request)
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceAssistantUnavailableError as exc:
        raise workspace_assistant_unavailable_exception(exc) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/handoff",
    response_model=WorkspaceLifecycleHandoffResponse,
    tags=["Advisory Workspace"],
    summary="Handoff Advisory Workspace to Proposal Lifecycle",
    description=(
        "Persists the current advisory workspace draft into proposal lifecycle without duplicating "
        "lifecycle ownership. The first handoff creates a proposal; later handoffs create new "
        "versions."
    ),
    responses=WORKSPACE_HANDOFF_RESPONSES,
)
def handoff_workspace(
    workspace_id: Annotated[
        str,
        Path(description="Workspace session identifier.", examples=["aws_001"]),
    ],
    request: WorkspaceLifecycleHandoffRequest,
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description=(
                "Required for the first workspace handoff to create a persisted proposal; "
                "optional for later version handoffs."
            ),
            examples=["workspace-handoff-idem-001"],
        ),
    ] = None,
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id captured in proposal lifecycle handoff audit.",
            examples=["corr-workspace-handoff-001"],
        ),
    ] = None,
    proposal_service: ProposalWorkflowService = Depends(
        proposal_shared.get_proposal_workflow_service
    ),
) -> WorkspaceLifecycleHandoffResponse:
    proposal_shared._assert_lifecycle_enabled()
    try:
        return handoff_workspace_to_proposal_lifecycle(
            workspace_id=workspace_id,
            request=request,
            proposal_service=proposal_service,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except WorkspaceNotFoundError as exc:
        raise workspace_not_found_exception(exc) from exc
    except WorkspaceLifecycleHandoffUnavailableError as exc:
        raise workspace_conflict_exception(exc) from exc
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)
