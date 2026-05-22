from src.api.services.workspace_service import get_workspace_session
from src.core.workspace.assistant_evidence import build_workspace_assistant_evidence
from src.core.workspace.models import (
    WorkspaceAssistantRequest,
    WorkspaceAssistantResponse,
    WorkspaceAssistantWorkflowPackRunReviewActionRequest,
    WorkspaceAssistantWorkflowPackRunReviewActionResponse,
)
from src.integrations.lotus_ai import (
    LotusAIRationaleUnavailableError,
    apply_workspace_rationale_review_action_with_lotus_ai,
    generate_workspace_rationale_with_lotus_ai,
)


class WorkspaceAssistantUnavailableError(Exception):
    pass


def generate_workspace_rationale(
    workspace_id: str,
    request: WorkspaceAssistantRequest,
) -> WorkspaceAssistantResponse:
    session = get_workspace_session(workspace_id)
    evidence = build_workspace_assistant_evidence(session)
    if evidence is None:
        raise WorkspaceAssistantUnavailableError("WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE")

    try:
        return generate_workspace_rationale_with_lotus_ai(
            request=request,
            evidence=evidence,
        )
    except LotusAIRationaleUnavailableError as exc:
        raise WorkspaceAssistantUnavailableError(str(exc)) from exc


def apply_workspace_rationale_review_action(
    workspace_id: str,
    request: WorkspaceAssistantWorkflowPackRunReviewActionRequest,
) -> WorkspaceAssistantWorkflowPackRunReviewActionResponse:
    get_workspace_session(workspace_id)

    try:
        return apply_workspace_rationale_review_action_with_lotus_ai(request)
    except LotusAIRationaleUnavailableError as exc:
        raise WorkspaceAssistantUnavailableError(str(exc)) from exc
