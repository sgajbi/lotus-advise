from decimal import Decimal
from types import SimpleNamespace

from src.core.workspace.evaluation import (
    build_evaluation_summary,
    calculate_blocking_issue_count,
    calculate_review_issue_count,
    format_portfolio_delta,
)
from src.core.workspace.models import WorkspaceDraftState, WorkspaceSession


def _rule(*, severity: str, status: str):
    return SimpleNamespace(severity=severity, status=status)


def test_workspace_evaluation_counts_blocking_and_review_issues():
    result = SimpleNamespace(
        rule_results=[
            _rule(severity="HARD", status="FAIL"),
            _rule(severity="SOFT", status="FAIL"),
            _rule(severity="INFO", status="FAIL"),
            _rule(severity="SOFT", status="PASS"),
        ],
        suitability=SimpleNamespace(issues=[object(), object()]),
    )

    assert calculate_blocking_issue_count(result) == 1
    assert calculate_review_issue_count(result) == 3


def test_workspace_evaluation_formats_portfolio_delta_without_reconciliation():
    result = SimpleNamespace(
        reconciliation=None,
        after_simulated=SimpleNamespace(
            total_value=SimpleNamespace(amount=Decimal("120.00")),
        ),
        before=SimpleNamespace(
            total_value=SimpleNamespace(amount=Decimal("100.00")),
        ),
    )

    assert format_portfolio_delta(result) == "20.00"


def test_workspace_evaluation_summary_uses_draft_counts_and_status():
    result = SimpleNamespace(
        status="PENDING_REVIEW",
        gate_decision=None,
        rule_results=[_rule(severity="SOFT", status="FAIL")],
        suitability=None,
        reconciliation=None,
        after_simulated=SimpleNamespace(
            total_value=SimpleNamespace(amount=Decimal("125.00")),
        ),
        before=SimpleNamespace(
            total_value=SimpleNamespace(amount=Decimal("100.00")),
        ),
    )
    session = WorkspaceSession.model_construct(
        draft_state=WorkspaceDraftState.model_validate(
            {
                "trade_drafts": [
                    {
                        "workspace_trade_id": "wtd_001",
                        "trade": {"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"},
                    }
                ],
                "cash_flow_drafts": [
                    {
                        "workspace_cash_flow_id": "wcf_001",
                        "cash_flow": {"currency": "USD", "amount": "250"},
                    }
                ],
            }
        )
    )

    summary = build_evaluation_summary(result, session)

    assert summary.status == "PENDING_REVIEW"
    assert summary.review_issue_count == 1
    assert summary.blocking_issue_count == 0
    assert summary.impact_summary.trade_count == 1
    assert summary.impact_summary.cash_flow_count == 1
    assert summary.impact_summary.portfolio_value_delta_base_ccy == "25.00"
