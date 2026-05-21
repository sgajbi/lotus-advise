from decimal import Decimal
from typing import Any, Protocol

from src.core.models import ProposalResult
from src.core.workspace.models import (
    WorkspaceEvaluationImpactSummary,
    WorkspaceEvaluationSummary,
    WorkspaceSession,
)


class _MoneyLike(Protocol):
    amount: Decimal


class _StateLike(Protocol):
    total_value: _MoneyLike


class _ResultWithPortfolioValues(Protocol):
    reconciliation: Any | None
    after_simulated: _StateLike
    before: _StateLike


def build_evaluation_summary(
    result: ProposalResult,
    session: WorkspaceSession,
) -> WorkspaceEvaluationSummary:
    return WorkspaceEvaluationSummary(
        status=result.status,
        gate_decision=result.gate_decision.model_copy(deep=True) if result.gate_decision else None,
        blocking_issue_count=calculate_blocking_issue_count(result),
        review_issue_count=calculate_review_issue_count(result),
        impact_summary=WorkspaceEvaluationImpactSummary(
            portfolio_value_delta_base_ccy=format_portfolio_delta(result),
            trade_count=len(session.draft_state.trade_drafts),
            cash_flow_count=len(session.draft_state.cash_flow_drafts),
        ),
    )


def calculate_review_issue_count(result: ProposalResult) -> int:
    soft_fail_count = sum(
        1
        for rule_result in result.rule_results
        if rule_result.status == "FAIL" and rule_result.severity == "SOFT"
    )
    suitability_issue_count = (
        len(result.suitability.issues) if result.suitability is not None else 0
    )
    return soft_fail_count + suitability_issue_count


def calculate_blocking_issue_count(result: ProposalResult) -> int:
    return sum(
        1
        for rule_result in result.rule_results
        if rule_result.status == "FAIL" and rule_result.severity == "HARD"
    )


def format_portfolio_delta(result: _ResultWithPortfolioValues) -> str:
    if result.reconciliation is not None:
        return str(result.reconciliation.delta.amount)
    delta = result.after_simulated.total_value.amount - result.before.total_value.amount
    return str(delta.quantize(Decimal("0.01")))
