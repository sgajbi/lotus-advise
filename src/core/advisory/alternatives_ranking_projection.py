from typing import Any

from src.core.advisory.alternatives_comparison_projection import build_comparison_summary
from src.core.advisory.alternatives_models import (
    AlternativeComparatorInputs,
    AlternativeRankingProjection,
    ProposalAlternative,
)
from src.core.advisory.alternatives_strategies import AlternativeCandidateSeed
from src.core.proposal_result_models import ProposalResult

READY_ALTERNATIVE_STATUSES = {"FEASIBLE", "FEASIBLE_WITH_REVIEW"}
RANKING_POLICY_VERSION = "advisory-ranking.2026-04"


def rank_alternatives(
    *,
    baseline_result: ProposalResult,
    alternatives: list[ProposalAlternative],
    candidate_seeds: tuple[AlternativeCandidateSeed, ...],
    selected_alternative_id: str | None,
) -> list[ProposalAlternative]:
    objective_order = candidate_objective_order(candidate_seeds)
    ordered = sorted(
        alternatives,
        key=lambda alternative: ranking_key(
            alternative=alternative,
            objective_rank=objective_order.get(alternative.alternative_id, 999),
        ),
    )

    ranked_ids = ready_alternative_ids(ordered)
    next_rank = 1
    for alternative in ordered:
        objective_rank = objective_order.get(alternative.alternative_id, 999)
        apply_ranking_projection(
            baseline_result=baseline_result,
            alternative=alternative,
            objective_rank=objective_rank,
            ranked_ids=ranked_ids,
        )
        if is_ready_alternative(alternative):
            alternative.rank = next_rank
            next_rank += 1
        else:
            alternative.rank = None
        alternative.selected = selected_ranked_alternative(
            alternative=alternative,
            selected_alternative_id=selected_alternative_id,
        )
    return ordered


def candidate_objective_order(
    candidate_seeds: tuple[AlternativeCandidateSeed, ...],
) -> dict[str, int]:
    return {
        seed.candidate_id: int(seed.metadata.get("objective_rank", index))
        for index, seed in enumerate(candidate_seeds)
    }


def ready_alternative_ids(alternatives: list[ProposalAlternative]) -> list[str]:
    return [
        alternative.alternative_id
        for alternative in alternatives
        if is_ready_alternative(alternative)
    ]


def is_ready_alternative(alternative: ProposalAlternative) -> bool:
    return alternative.status in READY_ALTERNATIVE_STATUSES


def apply_ranking_projection(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
    objective_rank: int,
    ranked_ids: list[str],
) -> None:
    alternative.ranking_policy_version = RANKING_POLICY_VERSION
    alternative.comparison_summary = build_comparison_summary(
        baseline_result=baseline_result,
        alternative=alternative,
    )
    alternative.ranking_projection = AlternativeRankingProjection(
        ranking_reason_codes=ranking_reason_codes(alternative=alternative),
        ranked_against_alternative_ids=[
            alternative_id
            for alternative_id in ranked_ids
            if alternative_id != alternative.alternative_id
        ],
        comparator_inputs=comparator_inputs(
            alternative=alternative,
            objective_rank=objective_rank,
        ),
    )


def selected_ranked_alternative(
    *,
    alternative: ProposalAlternative,
    selected_alternative_id: str | None,
) -> bool:
    return (
        selected_alternative_id is not None
        and selected_alternative_id == alternative.alternative_id
        and alternative.rank is not None
    )


def ranking_key(*, alternative: ProposalAlternative, objective_rank: int) -> tuple[Any, ...]:
    comparator_values = comparator_inputs(alternative=alternative, objective_rank=objective_rank)
    return (
        comparator_values.status_priority,
        comparator_values.missing_evidence_count,
        comparator_values.blocking_approval_count,
        comparator_values.approval_count,
        comparator_values.turnover_trade_count,
        objective_rank,
        alternative.alternative_id,
    )


def comparator_inputs(
    *, alternative: ProposalAlternative, objective_rank: int
) -> AlternativeComparatorInputs:
    summary = alternative.proposal_decision_summary
    approval_requirements = summary.get("approval_requirements", [])
    missing_evidence = summary.get("missing_evidence", [])
    if alternative.status == "FEASIBLE":
        status_priority = 0
    elif alternative.status == "FEASIBLE_WITH_REVIEW":
        status_priority = 1
    else:
        status_priority = 2
    return AlternativeComparatorInputs(
        status_priority=status_priority,
        decision_status=str(summary.get("decision_status", "UNKNOWN")),
        approval_count=len(approval_requirements),
        blocking_approval_count=sum(
            1 for item in approval_requirements if item.get("blocking_until_approved") is True
        ),
        missing_evidence_count=len(missing_evidence),
        turnover_trade_count=len(alternative.intents),
        objective_rank=objective_rank,
    )


def ranking_reason_codes(*, alternative: ProposalAlternative) -> list[str]:
    summary = alternative.proposal_decision_summary
    reason_codes = [f"STATUS_{alternative.status}"]
    decision_status = summary.get("decision_status")
    if isinstance(decision_status, str):
        reason_codes.append(f"DECISION_{decision_status}")
    if summary.get("approval_requirements"):
        reason_codes.append("APPROVALS_INCREASE_REVIEW_POSTURE")
    if summary.get("missing_evidence"):
        reason_codes.append("MISSING_EVIDENCE_LOWERS_RANK")
    if len(alternative.intents) <= 1:
        reason_codes.append("LOWER_TURNOVER_TIEBREAKER")
    return reason_codes


__all__ = [
    "RANKING_POLICY_VERSION",
    "READY_ALTERNATIVE_STATUSES",
    "apply_ranking_projection",
    "candidate_objective_order",
    "comparator_inputs",
    "is_ready_alternative",
    "rank_alternatives",
    "ranking_key",
    "ranking_reason_codes",
    "ready_alternative_ids",
    "selected_ranked_alternative",
]
