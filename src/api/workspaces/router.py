from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

import src.api.proposals.router as proposal_shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.api.services.workspace_ai_service import (
    WorkspaceAssistantUnavailableError,
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
    get_workspace_session,
    handoff_workspace_to_proposal_lifecycle,
    list_workspace_saved_versions,
    reevaluate_workspace_session,
    resume_workspace_version,
    save_workspace_version,
)
from src.core.proposals import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
    ProposalWorkflowService,
)
from src.core.workspace.models import (
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
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

_WORKSPACE_CREATE_EXAMPLE = {
    "summary": "Create a stateful advisory workspace",
    "value": {
        "workspace_name": "Q2 2026 growth reallocation draft",
        "created_by": "advisor_123",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_advisory_01",
            "household_id": "hh_001",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_growth_01",
        },
    },
}

_WORKSPACE_ADD_TRADE_EXAMPLE = {
    "summary": "Add a draft trade and re-evaluate the workspace",
    "value": {
        "actor_id": "advisor_123",
        "action_type": "ADD_TRADE",
        "trade": {
            "intent_type": "SECURITY_TRADE",
            "side": "BUY",
            "instrument_id": "EQ_GROWTH",
            "quantity": "25",
        },
    },
}

_WORKSPACE_SAVE_EXAMPLE = {
    "summary": "Save the current advisory workspace draft",
    "value": {
        "saved_by": "advisor_123",
        "version_label": "Initial sandbox draft",
    },
}

_WORKSPACE_RESUME_EXAMPLE = {
    "summary": "Resume a previously saved workspace version",
    "value": {
        "actor_id": "advisor_123",
        "workspace_version_id": "awv_001",
    },
}

_WORKSPACE_COMPARE_EXAMPLE = {
    "summary": "Compare the current draft to a saved baseline",
    "value": {
        "workspace_version_id": "awv_001",
    },
}

_WORKSPACE_HANDOFF_EXAMPLE = {
    "summary": "Persist the current workspace into proposal lifecycle",
    "value": {
        "handoff_by": "advisor_123",
        "metadata": {
            "title": "Q2 2026 growth reallocation proposal",
            "advisor_notes": "Prepared after client review call with growth tilt preference.",
            "jurisdiction": "SG",
            "mandate_id": "mandate_growth_01",
        },
    },
}

_WORKSPACE_AI_RATIONALE_EXAMPLE = {
    "summary": "Generate an evidence-grounded workspace rationale",
    "value": {
        "requested_by": "advisor_123",
        "instruction": "Summarize the proposal rationale for an advisor review note.",
    },
}


def _resolve_workspace_or_404(workspace_id: str) -> WorkspaceSession:
    try:
        return get_workspace_session(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _raise_saved_version_not_found(exc: WorkspaceSavedVersionNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


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
    responses={
        201: {
            "description": "Advisory workspace session created successfully.",
            "content": {
                "application/json": {"examples": {"stateful_workspace": _WORKSPACE_CREATE_EXAMPLE}}
            },
        },
        422: {"description": "Validation error for invalid workspace contract payloads."},
    },
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
    responses={404: {"description": "Workspace session not found."}},
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
    responses={
        200: {
            "description": "Workspace draft action applied successfully.",
            "content": {
                "application/json": {"examples": {"add_trade": _WORKSPACE_ADD_TRADE_EXAMPLE}}
            },
        },
        404: {"description": "Workspace session or targeted draft item not found."},
        409: {
            "description": "Workspace evaluation is not available for the current workspace mode."
        },
        422: {"description": "Validation error for invalid draft action payloads."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceEvaluationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/evaluate",
    response_model=WorkspaceSession,
    tags=["Advisory Workspace"],
    summary="Re-evaluate an Advisory Workspace Session",
    description=(
        "Runs deterministic re-evaluation for the current workspace draft and returns the updated "
        "workspace session with normalized evaluation outputs."
    ),
    responses={
        200: {"description": "Workspace re-evaluated successfully."},
        404: {"description": "Workspace session not found."},
        409: {
            "description": "Workspace evaluation is not available for the current workspace mode."
        },
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceEvaluationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/save",
    response_model=WorkspaceSaveResponse,
    tags=["Advisory Workspace"],
    summary="Save an Advisory Workspace Version",
    description=(
        "Captures the current advisory workspace draft as a saved version with replay-safe "
        "evidence for resume and compare workflows."
    ),
    responses={
        200: {
            "description": "Workspace version saved successfully.",
            "content": {
                "application/json": {"examples": {"save_version": _WORKSPACE_SAVE_EXAMPLE}}
            },
        },
        404: {"description": "Workspace session not found."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/advisory/workspaces/{workspace_id}/saved-versions",
    response_model=WorkspaceSavedVersionListResponse,
    tags=["Advisory Workspace"],
    summary="List Saved Advisory Workspace Versions",
    description=(
        "Returns saved advisory workspace versions available for support, compare, and resume "
        "workflows."
    ),
    responses={404: {"description": "Workspace session not found."}},
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/advisory/workspaces/{workspace_id}/resume",
    response_model=WorkspaceSession,
    tags=["Advisory Workspace"],
    summary="Resume a Saved Advisory Workspace Version",
    description=(
        "Restores a saved advisory workspace version into the current editable draft session."
    ),
    responses={
        200: {
            "description": "Workspace version resumed successfully.",
            "content": {
                "application/json": {"examples": {"resume_version": _WORKSPACE_RESUME_EXAMPLE}}
            },
        },
        404: {"description": "Workspace session or saved workspace version not found."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceSavedVersionNotFoundError as exc:
        raise _raise_saved_version_not_found(exc)


@router.post(
    "/advisory/workspaces/{workspace_id}/compare",
    response_model=WorkspaceCompareResponse,
    tags=["Advisory Workspace"],
    summary="Compare Current Workspace Draft to a Saved Version",
    description=(
        "Returns a deterministic comparison between the current advisory workspace draft and a "
        "saved workspace version baseline."
    ),
    responses={
        200: {
            "description": "Workspace comparison created successfully.",
            "content": {
                "application/json": {"examples": {"compare_version": _WORKSPACE_COMPARE_EXAMPLE}}
            },
        },
        404: {"description": "Workspace session or saved workspace version not found."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceSavedVersionNotFoundError as exc:
        raise _raise_saved_version_not_found(exc)


@router.post(
    "/advisory/workspaces/{workspace_id}/assistant/rationale",
    response_model=WorkspaceAssistantResponse,
    tags=["Advisory Workspace"],
    summary="Generate an Advisory Workspace Rationale",
    description=(
        "Builds an evidence-grounded workspace rationale through the Lotus AI seam using the "
        "current evaluated workspace state. The returned output always includes the deterministic "
        "evidence bundle that was supplied to the AI workflow."
    ),
    responses={
        200: {
            "description": "Workspace rationale generated successfully.",
            "content": {
                "application/json": {
                    "examples": {"workspace_rationale": _WORKSPACE_AI_RATIONALE_EXAMPLE}
                }
            },
        },
        404: {"description": "Workspace session not found."},
        409: {"description": "Workspace is not yet ready for AI assistance."},
        503: {"description": "Lotus AI assistance is unavailable for this runtime."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceAssistantUnavailableError as exc:
        detail = str(exc)
        if detail == "LOTUS_AI_RATIONALE_UNAVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=detail,
            ) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc


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
    responses={
        200: {
            "description": "Workspace handed off to proposal lifecycle successfully.",
            "content": {"application/json": {"examples": {"handoff": _WORKSPACE_HANDOFF_EXAMPLE}}},
        },
        404: {"description": "Workspace session or linked proposal not found."},
        409: {"description": "Workspace handoff is unavailable for the current workspace state."},
        422: {"description": "Lifecycle validation failed for the current workspace draft."},
    },
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkspaceLifecycleHandoffUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)
