from src.core.workspace.assistant_models import WorkspaceAssistantEvidence
from src.core.workspace.session_models import WorkspaceSession


def build_workspace_assistant_evidence(
    session: WorkspaceSession,
) -> WorkspaceAssistantEvidence | None:
    if session.evaluation_summary is None or session.latest_proposal_result is None:
        return None

    return WorkspaceAssistantEvidence(
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
