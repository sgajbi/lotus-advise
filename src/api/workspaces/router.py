from typing import Annotated, Optional

from fastapi import APIRouter, Header, status

from src.api.services.workspace_service import create_workspace_session
from src.core.workspace.models import WorkspaceSessionCreateRequest, WorkspaceSessionCreateResponse

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
