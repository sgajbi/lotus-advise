from decimal import Decimal
from typing import Any

from src.core.advisory.alternatives_models import (
    AlternativeComparisonSummary,
    ProposalAlternative,
)
from src.core.proposal_result_models import ProposalResult


def build_comparison_summary(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> AlternativeComparisonSummary:
    improvements: list[str] = []
    deteriorations: list[str] = []
    baseline_approval_count, alternative_approval_count = approval_requirement_counts(
        baseline_result=baseline_result,
        alternative=alternative,
    )
    _append_count_delta_messages(
        baseline_count=baseline_approval_count,
        alternative_count=alternative_approval_count,
        improvement_message="Approval burden is lower than the baseline proposal.",
        deterioration_message="Approval burden is higher than the baseline proposal.",
        improvements=improvements,
        deteriorations=deteriorations,
    )
    _append_count_delta_messages(
        baseline_count=baseline_missing_evidence_count(baseline_result),
        alternative_count=alternative_missing_evidence_count(alternative),
        improvement_message="Evidence completeness is stronger than the baseline proposal.",
        deterioration_message="Evidence completeness is weaker than the baseline proposal.",
        improvements=improvements,
        deteriorations=deteriorations,
    )

    risk_delta = risk_delta_for_alternative(
        baseline_result=baseline_result, alternative=alternative
    )
    _append_decimal_delta_messages(
        raw_delta=risk_delta.get("top_position_weight_delta_improvement"),
        improvement_message="Single-name concentration is lower than the baseline proposal.",
        deterioration_message="Single-name concentration is higher than the baseline proposal.",
        improvements=improvements,
        deteriorations=deteriorations,
    )

    cash_delta = cash_delta_for_alternative(
        baseline_result=baseline_result, alternative=alternative
    )
    _append_decimal_delta_messages(
        raw_delta=cash_delta.get("base_currency_cash_delta"),
        improvement_message="Base-currency cash is higher than the baseline proposal.",
        deterioration_message="Base-currency cash is lower than the baseline proposal.",
        improvements=improvements,
        deteriorations=deteriorations,
    )

    return AlternativeComparisonSummary(
        headline=f"{alternative.label} for {alternative.objective.lower().replace('_', ' ')}",
        primary_tradeoff=primary_tradeoff_for_alternative(alternative=alternative),
        improvements=improvements,
        deteriorations=deteriorations,
        unchanged_material_factors=unchanged_factors_for_alternative(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        approval_delta={
            "baseline_approval_count": baseline_approval_count,
            "alternative_approval_count": alternative_approval_count,
            "delta": alternative_approval_count - baseline_approval_count,
        },
        risk_delta=risk_delta,
        allocation_delta=allocation_delta_for_alternative(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        cash_delta=cash_delta,
        currency_delta=currency_delta_for_alternative(
            baseline_result=baseline_result,
            alternative=alternative,
        ),
        cost_delta={"status": "NOT_AVAILABLE"},
        evidence_refs=list(alternative.evidence_refs),
    )


def approval_requirement_counts(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> tuple[int, int]:
    baseline_summary = baseline_result.proposal_decision_summary
    baseline_count = (
        len(baseline_summary.approval_requirements) if baseline_summary is not None else 0
    )
    alternative_count = len(
        alternative.proposal_decision_summary.get("approval_requirements", [])
    )
    return baseline_count, alternative_count


def baseline_missing_evidence_count(baseline_result: ProposalResult) -> int:
    baseline_summary = baseline_result.proposal_decision_summary
    return len(baseline_summary.missing_evidence) if baseline_summary is not None else 0


def alternative_missing_evidence_count(alternative: ProposalAlternative) -> int:
    return len(alternative.proposal_decision_summary.get("missing_evidence", []))


def _append_count_delta_messages(
    *,
    baseline_count: int,
    alternative_count: int,
    improvement_message: str,
    deterioration_message: str,
    improvements: list[str],
    deteriorations: list[str],
) -> None:
    if alternative_count < baseline_count:
        improvements.append(improvement_message)
    elif alternative_count > baseline_count:
        deteriorations.append(deterioration_message)


def _append_decimal_delta_messages(
    *,
    raw_delta: Any,
    improvement_message: str,
    deterioration_message: str,
    improvements: list[str],
    deteriorations: list[str],
) -> None:
    if raw_delta is None:
        return
    delta = Decimal(str(raw_delta))
    if delta > Decimal("0"):
        improvements.append(improvement_message)
    elif delta < Decimal("0"):
        deteriorations.append(deterioration_message)


def primary_tradeoff_for_alternative(*, alternative: ProposalAlternative) -> str:
    if alternative.status == "FEASIBLE":
        return "Alternative is feasible without additional review posture."
    if alternative.status == "FEASIBLE_WITH_REVIEW":
        return "Alternative remains feasible but requires additional review posture."
    return "Alternative is not ranked because policy posture does not support recommendation."


def unchanged_factors_for_alternative(
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


def risk_delta_for_alternative(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    baseline_weight = top_position_weight(
        baseline_result.explanation.get("risk_lens", {}),
        "top_position_weight_proposed",
    )
    alternative_weight = top_position_weight(
        alternative.proposal_decision_summary.get("risk_posture", {}),
        "top_position_weight_proposed",
    )
    if alternative_weight is None:
        alternative_weight = top_position_weight_from_evidence_refs(alternative)
    return {
        "baseline_top_position_weight": baseline_weight,
        "alternative_top_position_weight": alternative_weight,
        "top_position_weight_delta_improvement": (
            (baseline_weight - alternative_weight)
            if baseline_weight is not None and alternative_weight is not None
            else None
        ),
    }


def allocation_delta_for_alternative(
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


def cash_delta_for_alternative(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    base_currency = baseline_result.after_simulated.total_value.currency
    baseline_cash = cash_balance_amount(
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


def currency_delta_for_alternative(
    *,
    baseline_result: ProposalResult,
    alternative: ProposalAlternative,
) -> dict[str, Any]:
    base_currency = baseline_result.after_simulated.total_value.currency
    baseline_weight = allocation_bucket_weight(
        baseline_result.after_simulated.allocation_views,
        "currency",
        base_currency,
    )
    return {
        "base_currency": base_currency,
        "baseline_weight": str(baseline_weight) if baseline_weight is not None else None,
        "alternative_weight": str(baseline_weight) if baseline_weight is not None else None,
    }


def top_position_weight(risk_payload: Any, field_name: str) -> Decimal | None:
    if not isinstance(risk_payload, dict):
        return None
    single_position = risk_payload.get("single_position_concentration")
    if not isinstance(single_position, dict):
        return None
    value = single_position.get(field_name)
    if value is None:
        return None
    return Decimal(str(value))


def top_position_weight_from_evidence_refs(alternative: ProposalAlternative) -> Decimal | None:
    return None


def cash_balance_amount(cash_balances: Any, currency: str) -> Decimal:
    for balance in cash_balances:
        if balance.currency == currency:
            return Decimal(str(balance.amount))
    return Decimal("0")


def allocation_bucket_weight(
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


__all__ = [
    "allocation_bucket_weight",
    "allocation_delta_for_alternative",
    "build_comparison_summary",
    "cash_balance_amount",
    "cash_delta_for_alternative",
    "currency_delta_for_alternative",
    "primary_tradeoff_for_alternative",
    "risk_delta_for_alternative",
    "top_position_weight",
    "top_position_weight_from_evidence_refs",
    "unchanged_factors_for_alternative",
]
