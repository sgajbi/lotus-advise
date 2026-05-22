from types import SimpleNamespace

from src.core.workspace.assistant_evidence import build_workspace_assistant_evidence
from src.core.workspace.models import (
    WorkspaceDraftState,
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceResolvedContext,
    WorkspaceSession,
    WorkspaceStatelessInput,
)


def _session(
    *,
    evaluation_summary: WorkspaceEvaluationSummary | None,
    latest_proposal_result: object | None,
) -> WorkspaceSession:
    return WorkspaceSession.model_construct(
        workspace_id="aws_001",
        workspace_name="Advisor review workspace",
        lifecycle_state="ACTIVE",
        input_mode="stateless",
        created_by="advisor_123",
        created_at="2026-03-25T09:30:00+00:00",
        stateless_input=WorkspaceStatelessInput.model_validate(
            {
                "simulate_request": {
                    "portfolio_snapshot": {
                        "portfolio_id": "pf_001",
                        "base_currency": "USD",
                        "positions": [],
                        "cash_balances": [{"currency": "USD", "amount": "1000"}],
                    },
                    "market_data_snapshot": {"prices": [], "fx_rates": []},
                    "shelf_entries": [],
                    "options": {"enable_proposal_simulation": True},
                    "proposed_cash_flows": [],
                    "proposed_trades": [],
                }
            }
        ),
        stateful_input=None,
        draft_state=WorkspaceDraftState(),
        resolved_context=WorkspaceResolvedContext(
            portfolio_id="pf_001",
            as_of="2026-03-25",
            portfolio_snapshot_id="ps_001",
        ),
        evaluation_summary=evaluation_summary,
        latest_proposal_result=latest_proposal_result,
    )


def _evaluation_summary() -> WorkspaceEvaluationSummary:
    return WorkspaceEvaluationSummary(
        status="READY",
        blocking_issue_count=0,
        review_issue_count=0,
        impact_summary=WorkspaceEvaluationImpactSummary(
            portfolio_value_delta_base_ccy="125.00",
            trade_count=1,
            cash_flow_count=0,
        ),
    )


def test_workspace_assistant_evidence_requires_evaluated_workspace() -> None:
    assert (
        build_workspace_assistant_evidence(
            _session(
                evaluation_summary=None,
                latest_proposal_result=SimpleNamespace(status="READY"),
            )
        )
        is None
    )
    assert (
        build_workspace_assistant_evidence(
            _session(evaluation_summary=_evaluation_summary(), latest_proposal_result=None)
        )
        is None
    )


def test_workspace_assistant_evidence_uses_deterministic_workspace_state() -> None:
    evidence = build_workspace_assistant_evidence(
        _session(
            evaluation_summary=_evaluation_summary(),
            latest_proposal_result=SimpleNamespace(status="PENDING_REVIEW"),
        )
    )

    assert evidence is not None
    assert evidence.workspace_id == "aws_001"
    assert evidence.proposal_status == "PENDING_REVIEW"
    assert evidence.evaluation_summary.status == "READY"
    assert evidence.resolved_context is not None
    assert evidence.resolved_context.portfolio_snapshot_id == "ps_001"
