from typing import Any, Literal

from src.core.advisory.alternatives_comparison_projection import (
    allocation_bucket_weight as _allocation_bucket_weight,  # noqa: F401
)
from src.core.advisory.alternatives_comparison_projection import (
    build_comparison_summary as _build_comparison_summary,  # noqa: F401
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
    ProposalAlternative,
    ProposalAlternatives,
)
from src.core.advisory.alternatives_normalizer import normalize_alternatives_request
from src.core.advisory.alternatives_projection_inputs import (
    build_strategy_inputs as _build_strategy_inputs,
)
from src.core.advisory.alternatives_ranking_projection import (
    RANKING_POLICY_VERSION as _RANKING_POLICY_VERSION,
)
from src.core.advisory.alternatives_ranking_projection import (
    comparator_inputs as _comparator_inputs,  # noqa: F401
)
from src.core.advisory.alternatives_ranking_projection import (
    rank_alternatives as _rank_alternatives,
)
from src.core.advisory.alternatives_ranking_projection import (
    ranking_reason_codes as _ranking_reason_codes,  # noqa: F401
)
from src.core.advisory.alternatives_strategies import build_candidate_plan
from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult


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
        selection_mode=_alternatives_selection_mode(request),
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
    rejected_candidates = _build_rejected_candidates(
        base_rejections=list(candidate_plan.rejected_candidates),
        evaluation_rejections=evaluation.rejected_candidates,
        include_evaluation_rejections=normalized_request.include_rejected_candidates,
    )

    return ProposalAlternatives(
        requested_objectives=list(normalized_request.requested_objectives),
        selected_alternative_id=normalized_request.selected_alternative_id,
        candidate_generation_policy_id=normalized_request.candidate_generation_policy_id,
        ranking_policy_id=normalized_request.ranking_policy_id or _RANKING_POLICY_VERSION,
        alternatives=ranked_alternatives,
        rejected_candidates=rejected_candidates,
        evidence_refs=_build_envelope_refs(ranked_alternatives, rejected_candidates),
    )


def _alternatives_selection_mode(
    request: ProposalSimulateRequest,
) -> Literal["generation", "selection"]:
    alternatives_request = request.alternatives_request
    if alternatives_request is None:
        return "generation"
    if alternatives_request.selected_alternative_id is None:
        return "generation"
    return "selection"


def _build_rejected_candidates(
    *,
    base_rejections: list[Any],
    evaluation_rejections: list[Any],
    include_evaluation_rejections: bool,
) -> list[Any]:
    if include_evaluation_rejections:
        return [*base_rejections, *evaluation_rejections]
    return base_rejections


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
