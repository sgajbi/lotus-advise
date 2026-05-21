from src.core.workspace.models import (
    WorkspaceCompareDiffSummary,
    WorkspaceCompareResponse,
    WorkspaceSavedVersion,
    WorkspaceSession,
)


def build_workspace_compare_response(
    *,
    session: WorkspaceSession,
    baseline_version: WorkspaceSavedVersion,
) -> WorkspaceCompareResponse:
    current_status = (
        session.evaluation_summary.status if session.evaluation_summary is not None else None
    )
    baseline_status = (
        baseline_version.evaluation_summary.status
        if baseline_version.evaluation_summary is not None
        else None
    )
    return WorkspaceCompareResponse(
        workspace_id=session.workspace_id,
        baseline_version=baseline_version.model_copy(deep=True),
        current_evaluation_summary=(
            session.evaluation_summary.model_copy(deep=True)
            if session.evaluation_summary is not None
            else None
        ),
        current_replay_evidence=(
            session.latest_replay_evidence.model_copy(deep=True)
            if session.latest_replay_evidence is not None
            else None
        ),
        diff_summary=WorkspaceCompareDiffSummary(
            trade_count_delta=(
                len(session.draft_state.trade_drafts)
                - len(baseline_version.draft_state.trade_drafts)
            ),
            cash_flow_count_delta=(
                len(session.draft_state.cash_flow_drafts)
                - len(baseline_version.draft_state.cash_flow_drafts)
            ),
            options_changed=session.draft_state.options != baseline_version.draft_state.options,
            reference_model_changed=(
                session.draft_state.reference_model != baseline_version.draft_state.reference_model
            ),
            evaluation_status_changed=current_status != baseline_status,
        ),
    )
