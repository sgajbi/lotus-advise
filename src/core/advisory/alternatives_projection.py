from typing import Any

from src.core.advisory.alternatives_comparison_projection import (
    allocation_bucket_weight as _allocation_bucket_weight,  # noqa: F401
)
from src.core.advisory.alternatives_comparison_projection import (
    build_comparison_summary as _build_comparison_summary,
)
from src.core.advisory.alternatives_comparison_projection import (
    cash_balance_amount as _cash_balance_amount,  # noqa: F401
)
from src.core.advisory.alternatives_comparison_projection import (
    primary_tradeoff_for_alternative as _primary_tradeoff,  # noqa: F401
)
from src.core.advisory.alternatives_comparison_projection import (
    top_position_weight as _top_position_weight,  # noqa: F401
)
from src.core.advisory.alternatives_enrichment import evaluate_alternative_candidates_batch
from src.core.advisory.alternatives_models import (
    AlternativeRankingProjection,
    ProposalAlternative,
    ProposalAlternatives,
)
from src.core.advisory.alternatives_normalizer import normalize_alternatives_request
from src.core.advisory.alternatives_projection_inputs import (
    build_strategy_inputs as _build_strategy_inputs,
)
from src.core.advisory.alternatives_strategies import (
    AlternativeCandidateSeed,
    build_candidate_plan,
)
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult

_READY_STATUSES = {"FEASIBLE", "FEASIBLE_WITH_REVIEW"}
_RANKING_POLICY_VERSION = "advisory-ranking.2026-04"


def build_proposal_alternatives(
    *,
    request: ProposalSimulateRequest,
    baseline_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None = None,
    policy_context: dict[str, object] | None = None,
    evaluator: Any | None = None,
) -> ProposalAlternatives | None:
    normalized_request = normalize_alternatives_request(
        request.alternatives_request,
        selection_mode=(
            "selection"
            if request.alternatives_request is not None
            and request.alternatives_request.selected_alternative_id is not None
            else "generation"
        ),
    )
    if normalized_request is None:
        return None

    strategy_inputs = _build_strategy_inputs(request)
    candidate_plan = build_candidate_plan(request=normalized_request, inputs=strategy_inputs)
    evaluation = evaluate_alternative_candidates_batch(
        base_request=request,
        normalized_request=normalized_request,
        candidates=list(candidate_plan.seeds),
        correlation_id=correlation_id,
        resolved_as_of=resolved_as_of,
        policy_context=policy_context,
        evaluator=evaluator,
    )
    ranked_alternatives = _rank_alternatives(
        baseline_result=baseline_result,
        alternatives=evaluation.alternatives,
        candidate_seeds=candidate_plan.seeds,
        selected_alternative_id=normalized_request.selected_alternative_id,
    )
    rejected_candidates = list(candidate_plan.rejected_candidates)
    if normalized_request.include_rejected_candidates:
        rejected_candidates.extend(evaluation.rejected_candidates)

    return ProposalAlternatives(
        requested_objectives=list(normalized_request.requested_objectives),
        selected_alternative_id=normalized_request.selected_alternative_id,
        candidate_generation_policy_id=normalized_request.candidate_generation_policy_id,
        ranking_policy_id=normalized_request.ranking_policy_id or _RANKING_POLICY_VERSION,
        alternatives=ranked_alternatives,
        rejected_candidates=rejected_candidates,
        evidence_refs=_build_envelope_refs(ranked_alternatives, rejected_candidates),
    )


def _rank_alternatives(
    *,
    baseline_result: ProposalResult,
    alternatives: list[ProposalAlternative],
    candidate_seeds: tuple[AlternativeCandidateSeed, ...],
    selected_alternative_id: str | None,
) -> list[ProposalAlternative]:
    objective_order = {
        seed.candidate_id: int(seed.metadata.get("objective_rank", index))
        for index, seed in enumerate(candidate_seeds)
    }
    ordered = sorted(
        alternatives,
        key=lambda alternative: _ranking_key(
            alternative=alternative,
            objective_rank=objective_order.get(alternative.alternative_id, 999),
        ),
    )

    ranked_ids = [item.alternative_id for item in ordered if item.status in _READY_STATUSES]
    next_rank = 1
    for alternative in ordered:
        comparator_inputs = _comparator_inputs(
            alternative=alternative,
            objective_rank=objective_order.get(alternative.alternative_id, 999),
        )
        alternative.ranking_policy_version = _RANKING_POLICY_VERSION
        alternative.comparison_summary = _build_comparison_summary(
            baseline_result=baseline_result,
            alternative=alternative,
        )
        alternative.ranking_projection = AlternativeRankingProjection(
            ranking_reason_codes=_ranking_reason_codes(alternative=alternative),
            ranked_against_alternative_ids=[
                alternative_id
                for alternative_id in ranked_ids
                if alternative_id != alternative.alternative_id
            ],
            comparator_inputs=comparator_inputs,
        )
        if alternative.status in _READY_STATUSES:
            alternative.rank = next_rank
            next_rank += 1
        else:
            alternative.rank = None
        alternative.selected = (
            selected_alternative_id is not None
            and selected_alternative_id == alternative.alternative_id
            and alternative.rank is not None
        )
    return ordered


def _ranking_key(*, alternative: ProposalAlternative, objective_rank: int) -> tuple[Any, ...]:
    comparator_inputs = _comparator_inputs(alternative=alternative, objective_rank=objective_rank)
    return (
        comparator_inputs["status_priority"],
        comparator_inputs["missing_evidence_count"],
        comparator_inputs["blocking_approval_count"],
        comparator_inputs["approval_count"],
        comparator_inputs["turnover_trade_count"],
        objective_rank,
        alternative.alternative_id,
    )


def _comparator_inputs(
    *, alternative: ProposalAlternative, objective_rank: int
) -> dict[str, int | str]:
    summary = alternative.proposal_decision_summary
    approval_requirements = summary.get("approval_requirements", [])
    missing_evidence = summary.get("missing_evidence", [])
    if alternative.status == "FEASIBLE":
        status_priority = 0
    elif alternative.status == "FEASIBLE_WITH_REVIEW":
        status_priority = 1
    else:
        status_priority = 2
    return {
        "status_priority": status_priority,
        "decision_status": str(summary.get("decision_status", "UNKNOWN")),
        "approval_count": len(approval_requirements),
        "blocking_approval_count": sum(
            1 for item in approval_requirements if item.get("blocking_until_approved") is True
        ),
        "missing_evidence_count": len(missing_evidence),
        "turnover_trade_count": len(alternative.intents),
        "objective_rank": objective_rank,
    }


def _ranking_reason_codes(*, alternative: ProposalAlternative) -> list[str]:
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


def _build_envelope_refs(
    alternatives: list[ProposalAlternative],
    rejected_candidates: list[Any],
) -> list[str]:
    refs: set[str] = set()
    for alternative in alternatives:
        refs.update(alternative.evidence_refs)
    for rejected_candidate in rejected_candidates:
        refs.update(rejected_candidate.evidence_refs)
    return sorted(refs)
