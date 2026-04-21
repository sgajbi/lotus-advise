from src.api.services.workspace_service import get_workspace_session
from src.core.workspace.models import (
    WorkspaceAssistantEvidence,
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
    if session.evaluation_summary is None or session.latest_proposal_result is None:
        raise WorkspaceAssistantUnavailableError("WORKSPACE_AI_REQUIRES_EVALUATED_WORKSPACE")

    evidence = WorkspaceAssistantEvidence(
        workspace_id=session.workspace_id,
        input_mode=session.input_mode,
        resolved_context=(
            session.resolved_context.model_copy(deep=True)
            if session.resolved_context is not None
            else None
        ),
        evaluation_summary=session.evaluation_summary.model_copy(deep=True),
        proposal_status=session.latest_proposal_result.status,
    )

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
