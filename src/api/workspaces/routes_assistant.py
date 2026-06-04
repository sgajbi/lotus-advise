from typing import cast

from fastapi import APIRouter

from src.api.services.workspace_ai_service import (
    apply_workspace_rationale_review_action,
    generate_workspace_rationale,
)
from src.api.workspaces.errors import run_workspace_operation
from src.api.workspaces.parameters import WorkspaceIdPath
from src.api.workspaces.response_metadata import (
    WORKSPACE_RATIONALE_RESPONSES,
    WORKSPACE_RATIONALE_REVIEW_RESPONSES,
)
from src.core.workspace.assistant_models import (
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
    WorkspaceAssistantWorkflowPackRunReviewActionRequest,
    WorkspaceAssistantWorkflowPackRunReviewActionResponse,
)

router = APIRouter()


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
    workspace_id: WorkspaceIdPath,
    request: WorkspaceAssistantRequest,
) -> WorkspaceAssistantResponse:
    return cast(
        WorkspaceAssistantResponse,
        run_workspace_operation(lambda: generate_workspace_rationale(workspace_id, request)),
    )


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
    workspace_id: WorkspaceIdPath,
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> WorkspaceAssistantWorkflowPackRunReviewActionResponse:
    return cast(
        WorkspaceAssistantWorkflowPackRunReviewActionResponse,
        run_workspace_operation(
            lambda: apply_workspace_rationale_review_action(workspace_id, request)
        ),
    )
