from src.core.workspace.compare import build_workspace_compare_response
from src.core.workspace.models import (
    WorkspaceDraftState,
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceSavedVersion,
    WorkspaceSession,
)


def _draft_state(
    *,
    trade_count: int,
    cash_flow_count: int,
    allow_restricted: bool,
) -> WorkspaceDraftState:
    return WorkspaceDraftState.model_validate(
        {
            "options": {
                "enable_proposal_simulation": True,
                "allow_restricted": allow_restricted,
            },
            "reference_model": (
                {
                    "model_id": "rm_growth",
                    "as_of": "2026-05-20",
                    "base_currency": "USD",
                }
                if cash_flow_count > 0
                else None
            ),
            "trade_drafts": [
                {
                    "workspace_trade_id": f"wtd_{index}",
                    "trade": {
                        "side": "BUY",
                        "instrument_id": f"EQ_{index}",
                        "quantity": "1",
                    },
                }
                for index in range(trade_count)
            ],
            "cash_flow_drafts": [
                {
                    "workspace_cash_flow_id": f"wcf_{index}",
                    "cash_flow": {"currency": "USD", "amount": "100.00"},
                }
                for index in range(cash_flow_count)
            ],
        }
    )


def _evaluation_summary(status: str) -> WorkspaceEvaluationSummary:
    return WorkspaceEvaluationSummary(
        status=status,
        gate_decision=None,
        blocking_issue_count=0,
        review_issue_count=0,
        impact_summary=WorkspaceEvaluationImpactSummary(
            portfolio_value_delta_base_ccy="0.00",
            trade_count=0,
            cash_flow_count=0,
        ),
    )


def test_workspace_compare_response_summarizes_draft_and_status_deltas() -> None:
    baseline = WorkspaceSavedVersion.model_construct(
        workspace_version_id="awv_baseline",
        draft_state=_draft_state(
            trade_count=1,
            cash_flow_count=1,
            allow_restricted=False,
        ),
        evaluation_summary=_evaluation_summary("READY"),
    )
    session = WorkspaceSession.model_construct(
        workspace_id="aws_current",
        draft_state=_draft_state(
            trade_count=2,
            cash_flow_count=0,
            allow_restricted=True,
        ),
        evaluation_summary=_evaluation_summary("PENDING_REVIEW"),
        latest_replay_evidence=None,
    )

    response = build_workspace_compare_response(
        session=session,
        baseline_version=baseline,
    )

    assert response.workspace_id == "aws_current"
    assert response.baseline_version is not baseline
    assert response.diff_summary.trade_count_delta == 1
    assert response.diff_summary.cash_flow_count_delta == -1
    assert response.diff_summary.options_changed is True
    assert response.diff_summary.reference_model_changed is True
    assert response.diff_summary.evaluation_status_changed is True
