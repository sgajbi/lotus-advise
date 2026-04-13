from decimal import Decimal
from typing import Any

from src.core.advisory.alternatives_enrichment import evaluate_alternative_candidates_batch
from src.core.advisory.alternatives_models import (
    AlternativeComparisonSummary,
    AlternativeRankingProjection,
    ProposalAlternative,
    ProposalAlternatives,
)
from src.core.advisory.alternatives_normalizer import normalize_alternatives_request
from src.core.advisory.alternatives_strategies import (
    AlternativeCandidateSeed,
    AlternativeStrategyInputs,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
    build_candidate_plan,
)
from src.core.models import ProposalResult, ProposalSimulateRequest

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


def _build_strategy_inputs(request: ProposalSimulateRequest) -> AlternativeStrategyInputs:
    prices_by_instrument = {
        price.instrument_id: price for price in request.market_data_snapshot.prices
    }
    return AlternativeStrategyInputs(
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        base_currency=request.portfolio_snapshot.base_currency,
        positions=tuple(
            StrategyPosition(
                instrument_id=position.instrument_id,
                quantity=position.quantity,
                price=(
                    prices_by_instrument[position.instrument_id].price
                    if position.instrument_id in prices_by_instrument
                    else None
                ),
                currency=(
                    prices_by_instrument[position.instrument_id].currency
                    if position.instrument_id in prices_by_instrument
                    else None
                ),
            )
            for position in request.portfolio_snapshot.positions
        ),
        cash_balances={
            balance.currency: balance.amount for balance in request.portfolio_snapshot.cash_balances
        },
        shelf_instruments=tuple(
            StrategyShelfInstrument(
                instrument_id=entry.instrument_id,
                status=entry.status,
                asset_class=entry.asset_class,
            )
            for entry in request.shelf_entries
        ),
        current_proposed_trades=tuple(
            StrategyTradeIntent(
                side=trade.side,
                instrument_id=trade.instrument_id,
                quantity=trade.quantity,
                notional_amount=(trade.notional.amount if trade.notional is not None else None),
                notional_currency=(trade.notional.currency if trade.notional is not None else None),
            )
            for trade in request.proposed_trades
        ),
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


def _build_comparison_summary(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> AlternativeComparisonSummary:
    baseline_summary = baseline_result.proposal_decision_summary
    baseline_approval_count = (
        len(baseline_summary.approval_requirements) if baseline_summary is not None else 0
    )
    alternative_summary = alternative.proposal_decision_summary
    alternative_approval_count = len(alternative_summary.get("approval_requirements", []))
    baseline_missing_evidence = (
        len(baseline_summary.missing_evidence) if baseline_summary is not None else 0
    )
    alternative_missing_evidence = len(alternative_summary.get("missing_evidence", []))

    improvements: list[str] = []
    deteriorations: list[str] = []

    if alternative_approval_count < baseline_approval_count:
        improvements.append("Approval burden is lower than the baseline proposal.")
    elif alternative_approval_count > baseline_approval_count:
        deteriorations.append("Approval burden is higher than the baseline proposal.")

    if alternative_missing_evidence < baseline_missing_evidence:
        improvements.append("Evidence completeness is stronger than the baseline proposal.")
    elif alternative_missing_evidence > baseline_missing_evidence:
        deteriorations.append("Evidence completeness is weaker than the baseline proposal.")

    risk_delta = _risk_delta(baseline_result=baseline_result, alternative=alternative)
    if risk_delta.get("top_position_weight_delta_improvement") is not None:
        if Decimal(str(risk_delta["top_position_weight_delta_improvement"])) > Decimal("0"):
            improvements.append("Single-name concentration is lower than the baseline proposal.")
        elif Decimal(str(risk_delta["top_position_weight_delta_improvement"])) < Decimal("0"):
            deteriorations.append("Single-name concentration is higher than the baseline proposal.")

    cash_delta = _cash_delta(baseline_result=baseline_result, alternative=alternative)
    if cash_delta.get("base_currency_cash_delta") is not None:
        delta = Decimal(str(cash_delta["base_currency_cash_delta"]))
        if delta > Decimal("0"):
            improvements.append("Base-currency cash is higher than the baseline proposal.")
        elif delta < Decimal("0"):
            deteriorations.append("Base-currency cash is lower than the baseline proposal.")

    return AlternativeComparisonSummary(
        headline=f"{alternative.label} for {alternative.objective.lower().replace('_', ' ')}",
        primary_tradeoff=_primary_tradeoff(alternative=alternative),
        improvements=improvements,
        deteriorations=deteriorations,
        unchanged_material_factors=_unchanged_factors(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        approval_delta={
            "baseline_approval_count": baseline_approval_count,
            "alternative_approval_count": alternative_approval_count,
            "delta": alternative_approval_count - baseline_approval_count,
        },
        risk_delta=risk_delta,
        allocation_delta=_allocation_delta(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        cash_delta=cash_delta,
        currency_delta=_currency_delta(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        cost_delta={"status": "NOT_AVAILABLE"},
        evidence_refs=list(alternative.evidence_refs),
    )


def _primary_tradeoff(*, alternative: ProposalAlternative) -> str:
    if alternative.status == "FEASIBLE":
        return "Alternative is feasible without additional review posture."
    if alternative.status == "FEASIBLE_WITH_REVIEW":
        return "Alternative remains feasible but requires additional review posture."
    return "Alternative is not ranked because policy posture does not support recommendation."


def _unchanged_factors(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> list[str]:
    unchanged: list[str] = []
    if alternative.proposal_decision_summary.get("top_level_status") == baseline_result.status:
        unchanged.append("Top-level proposal status is unchanged.")
    if baseline_result.explanation.get("authority_resolution") is not None:
        unchanged.append("Canonical upstream authorities remain unchanged.")
    return unchanged


def _risk_delta(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    baseline_weight = _top_position_weight(
        baseline_result.explanation.get("risk_lens", {}),
        "top_position_weight_proposed",
    )
    alternative_weight = _top_position_weight(
        alternative.proposal_decision_summary.get("risk_posture", {}),
        "top_position_weight_proposed",
    )
    if alternative_weight is None:
        alternative_weight = _top_position_weight_from_evidence_refs(alternative)
    return {
        "baseline_top_position_weight": baseline_weight,
        "alternative_top_position_weight": alternative_weight,
        "top_position_weight_delta_improvement": (
            (baseline_weight - alternative_weight)
            if baseline_weight is not None and alternative_weight is not None
            else None
        ),
    }


def _allocation_delta(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    baseline_total = baseline_result.after_simulated.total_value.amount
    alternative_total = baseline_total
    return {
        "baseline_total_value": str(baseline_total),
        "alternative_total_value": str(alternative_total),
    }


def _cash_delta(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    base_currency = baseline_result.after_simulated.total_value.currency
    baseline_cash = _cash_balance_amount(
        baseline_result.after_simulated.cash_balances,
        base_currency,
    )
    alternative_cash = baseline_cash
    return {
        "currency": base_currency,
        "baseline_cash": str(baseline_cash),
        "alternative_cash": str(alternative_cash),
        "base_currency_cash_delta": str(alternative_cash - baseline_cash),
    }


def _currency_delta(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    base_currency = baseline_result.after_simulated.total_value.currency
    baseline_weight = _allocation_bucket_weight(
        baseline_result.after_simulated.allocation_views,
        "currency",
        base_currency,
    )
    return {
        "base_currency": base_currency,
        "baseline_weight": str(baseline_weight) if baseline_weight is not None else None,
        "alternative_weight": str(baseline_weight) if baseline_weight is not None else None,
    }


def _top_position_weight(risk_payload: Any, field_name: str) -> Decimal | None:
    if not isinstance(risk_payload, dict):
        return None
    single_position = risk_payload.get("single_position_concentration")
    if not isinstance(single_position, dict):
        return None
    value = single_position.get(field_name)
    if value is None:
        return None
    return Decimal(str(value))


def _top_position_weight_from_evidence_refs(alternative: ProposalAlternative) -> Decimal | None:
    return None


def _cash_balance_amount(cash_balances: Any, currency: str) -> Decimal:
    for balance in cash_balances:
        if balance.currency == currency:
            return Decimal(str(balance.amount))
    return Decimal("0")


def _allocation_bucket_weight(
    allocation_views: Any,
    dimension: str,
    bucket_key: str,
) -> Decimal | None:
    for view in allocation_views:
        if view.dimension != dimension:
            continue
        for bucket in view.buckets:
            if bucket.key == bucket_key:
                return Decimal(str(bucket.weight))
    return None


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
