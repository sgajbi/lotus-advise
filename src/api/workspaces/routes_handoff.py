from typing import cast

from fastapi import APIRouter, Depends

import src.api.proposals.router as proposal_shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.api.services.workspace_service import handoff_workspace_to_proposal_lifecycle
from src.api.workspaces.errors import run_workspace_operation
from src.api.workspaces.parameters import (
    WorkspaceHandoffCorrelationIdHeader,
    WorkspaceHandoffIdempotencyKeyHeader,
    WorkspaceIdPath,
)
from src.api.workspaces.response_metadata import WORKSPACE_HANDOFF_RESPONSES
from src.core.proposals import ProposalWorkflowService
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.workspace.handoff_models import (
    WorkspaceLifecycleHandoffRequest,
    WorkspaceLifecycleHandoffResponse,
)

router = APIRouter()


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
    workspace_id: WorkspaceIdPath,
    request: WorkspaceLifecycleHandoffRequest,
    idempotency_key: WorkspaceHandoffIdempotencyKeyHeader = None,
    correlation_id: WorkspaceHandoffCorrelationIdHeader = None,
    proposal_service: ProposalWorkflowService = Depends(
        proposal_shared.get_proposal_workflow_service
    ),
) -> WorkspaceLifecycleHandoffResponse:
    proposal_shared._assert_lifecycle_enabled()
    try:
        return cast(
            WorkspaceLifecycleHandoffResponse,
            run_workspace_operation(
                lambda: handoff_workspace_to_proposal_lifecycle(
                    workspace_id=workspace_id,
                    request=request,
                    proposal_service=proposal_service,
                    idempotency_key=idempotency_key,
                    correlation_id=correlation_id,
                )
            ),
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)
        raise
