from typing import cast

from src.api.services.workspace_ai_errors import run_workspace_ai_operation
from src.api.services.workspace_errors import WorkspaceAssistantUnavailableError
from src.api.services.workspace_service import get_workspace_session
from src.core.workspace.assistant_evidence import build_workspace_assistant_evidence
from src.core.workspace.assistant_models import (
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
    WorkspaceAssistantWorkflowPackRunReviewActionRequest,
    WorkspaceAssistantWorkflowPackRunReviewActionResponse,
)
from src.integrations.lotus_ai import (
    apply_workspace_rationale_review_action_with_lotus_ai,
    generate_workspace_rationale_with_lotus_ai,
)


def generate_workspace_rationale(
    workspace_id: str,
    request: WorkspaceAssistantRequest,
) -> WorkspaceAssistantResponse:
    session = get_workspace_session(workspace_id)
    evidence = build_workspace_assistant_evidence(session)
    if evidence is None:
        raise WorkspaceAssistantUnavailableError("WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE")

    return cast(
        WorkspaceAssistantResponse,
        run_workspace_ai_operation(
            lambda: generate_workspace_rationale_with_lotus_ai(
                request=request,
                evidence=evidence,
            )
        ),
    )


def apply_workspace_rationale_review_action(
    workspace_id: str,
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> WorkspaceAssistantWorkflowPackRunReviewActionResponse:
    get_workspace_session(workspace_id)

    return cast(
        WorkspaceAssistantWorkflowPackRunReviewActionResponse,
        run_workspace_ai_operation(
            lambda: apply_workspace_rationale_review_action_with_lotus_ai(
                request,
                workspace_id=workspace_id,
            )
        ),
    )
