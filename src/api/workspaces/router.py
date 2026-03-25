from typing import Annotated, Optional

from fastapi import APIRouter, Header, HTTPException, Path, status

from src.api.services.workspace_service import (
    WorkspaceEvaluationUnavailableError,
    WorkspaceNotFoundError,
    apply_workspace_draft_action,
    create_workspace_session,
    get_workspace_session,
    reevaluate_workspace_session,
)
from src.core.workspace.models import (
    WorkspaceDraftActionRequest,
    WorkspaceDraftActionResponse,
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


def _resolve_workspace_or_404(workspace_id: str) -> WorkspaceSession:
    try:
        return get_workspace_session(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


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
            "content": {"application/json": {"examples": {"stateful_workspace": _WORKSPACE_CREATE_EXAMPLE}}},
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
            description="Optional trace and correlation identifier propagated through the advisory workflow.",
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
    description="Returns the current advisory workspace session, including draft state and latest evaluation.",
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
            "content": {"application/json": {"examples": {"add_trade": _WORKSPACE_ADD_TRADE_EXAMPLE}}},
        },
        404: {"description": "Workspace session or targeted draft item not found."},
        409: {"description": "Workspace evaluation is not available for the current workspace mode."},
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
        409: {"description": "Workspace evaluation is not available for the current workspace mode."},
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
