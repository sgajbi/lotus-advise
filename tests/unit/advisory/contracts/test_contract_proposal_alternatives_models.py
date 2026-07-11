import pytest
from pydantic import ValidationError

from src.core.advisory import (
    ProposalAlternative,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
)
from src.core.advisory.alternatives_models import (
    AlternativeAllocationDelta,
    AlternativeApprovalDelta,
    AlternativeCandidateSeed,
    AlternativeCashDelta,
    AlternativeComparatorInputs,
    AlternativeComparisonSummary,
    AlternativeConstraintResult,
    AlternativeCostDelta,
    AlternativeCurrencyDelta,
    AlternativeDecisionApprovalRequirementSnapshot,
    AlternativeDecisionMissingEvidenceSnapshot,
    AlternativeDecisionSummarySnapshot,
    AlternativeRankingProjection,
    AlternativeRiskDelta,
    AlternativeTradeoff,
    ProposalAlternatives,
    RejectedAlternativeCandidate,
    validate_alternative_decision_summary_snapshot,
    validate_alternative_simulation_intent_payload,
)


def test_alternatives_request_defaults_to_bounded_rejected_visible_contract():
    request = ProposalAlternativesRequest(objectives=["REDUCE_CONCENTRATION"])

    assert request.enabled is True
    assert request.max_alternatives == 3
    assert request.include_rejected_candidates is True
    assert request.objectives == ["REDUCE_CONCENTRATION"]


def test_alternatives_constraints_normalize_and_dedupe_lists():
    constraints = ProposalAlternativesConstraints(
        preserve_holdings=["ISIN:US0378331005", "ISIN:US0378331005", " "],
        restricted_instruments=["ISIN:US5949181045", "ISIN:US5949181045"],
        allowed_currencies=["usd", "USD", " eur "],
    )

    assert constraints.preserve_holdings == ["ISIN:US0378331005"]
    assert constraints.restricted_instruments == ["ISIN:US5949181045"]
    assert constraints.allowed_currencies == ["USD", "EUR"]


def test_alternatives_constraints_reject_float_and_out_of_range_turnover():
    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(max_turnover_pct=12.5)

    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(max_turnover_pct="150")


def test_alternative_money_constraint_rejects_float_amount():
    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(cash_floor={"amount": 25000.0, "currency": "USD"})


def test_alternative_money_constraint_rejects_non_positive_amount_and_blank_currency():
    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(cash_floor={"amount": "0", "currency": "USD"})

    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(cash_floor={"amount": "10", "currency": " "})


def test_alternatives_constraints_normalize_none_values_to_empty_lists():
    constraints = ProposalAlternativesConstraints(
        preserve_holdings=None,
        allowed_currencies=None,
    )

    assert constraints.preserve_holdings == []
    assert constraints.allowed_currencies == []


def test_alternatives_constraints_and_request_reject_scalar_list_fields():
    with pytest.raises(ValidationError):
        ProposalAlternativesConstraints(preserve_holdings="AAPL")

    with pytest.raises(ValidationError):
        ProposalAlternativesRequest(objectives="REDUCE_CONCENTRATION")

    with pytest.raises(ValidationError):
        ProposalAlternativesRequest(evidence_requirements="MANDATE_CONTEXT")


def test_alternatives_request_normalizes_none_lists_to_empty():
    request = ProposalAlternativesRequest(
        objectives=None,
        evidence_requirements=None,
    )

    assert request.objectives == []
    assert request.evidence_requirements == []


def test_proposal_alternative_allows_canonical_summary_payload_shape():
    alternative = ProposalAlternative(
        alternative_id="alt_reduce_concentration_pf_usd",
        label="Reduce concentration",
        objective="REDUCE_CONCENTRATION",
        status="FEASIBLE",
        construction_policy_version="advisory-construction.2026-04",
        ranking_policy_version="advisory-ranking.2026-04",
        proposal_decision_summary={
            "decision_status": "REQUIRES_RISK_REVIEW",
            "top_level_status": "PENDING_REVIEW",
        },
    )

    assert alternative.selected is False
    assert alternative.rank is None
    assert alternative.proposal_decision_summary["decision_status"] == "REQUIRES_RISK_REVIEW"


def test_alternative_decision_summary_snapshot_validates_known_governed_fields():
    snapshot = validate_alternative_decision_summary_snapshot(
        {
            "decision_status": "READY_FOR_CLIENT_REVIEW",
            "top_level_status": "READY",
            "approval_requirements": [{"approval_type": "RISK", "blocking_until_approved": True}],
            "missing_evidence": [{"reason_code": "MISSING_RISK_LENS"}],
            "risk_posture": {
                "single_position_concentration": {"top_position_weight_proposed": "0.10"}
            },
            "comparison_only_field": "preserved",
        }
    )

    assert snapshot["comparison_only_field"] == "preserved"
    assert (
        AlternativeDecisionSummarySnapshot.model_validate(snapshot).decision_status
        == "READY_FOR_CLIENT_REVIEW"
    )

    with pytest.raises(ValidationError):
        ProposalAlternative(
            alternative_id="alt_bad_summary",
            label="Bad summary",
            objective="REDUCE_CONCENTRATION",
            status="FEASIBLE",
            construction_policy_version="advisory-construction.2026-04",
            ranking_policy_version="advisory-ranking.2026-04",
            proposal_decision_summary={"decision_status": "READY"},
        )


def test_alternative_generated_simulation_intent_payloads_use_request_contracts():
    trade = validate_alternative_simulation_intent_payload(
        {
            "intent_type": "SECURITY_TRADE",
            "side": "BUY",
            "instrument_id": "EQ_NEW",
            "quantity": "4",
        }
    )
    cash_flow = validate_alternative_simulation_intent_payload(
        {"intent_type": "CASH_FLOW", "currency": "USD", "amount": "125.50"}
    )

    assert trade["intent_type"] == "SECURITY_TRADE"
    assert trade["quantity"] == "4"
    assert cash_flow["amount"] == "125.50"

    with pytest.raises(ValidationError):
        validate_alternative_simulation_intent_payload(
            {
                "intent_type": "SECURITY_TRADE",
                "side": "BUY",
                "instrument_id": "EQ_NEW",
            }
        )


def test_alternative_comparison_and_ranking_payloads_use_typed_contracts():
    summary = AlternativeComparisonSummary(
        headline="Reduce concentration",
        primary_tradeoff="Alternative is feasible.",
        approval_delta=AlternativeApprovalDelta(
            baseline_approval_count=1,
            alternative_approval_count=0,
            delta=-1,
        ),
        risk_delta=AlternativeRiskDelta(
            baseline_top_position_weight="0.30",
            alternative_top_position_weight="0.10",
            top_position_weight_delta_improvement="0.20",
        ),
        allocation_delta=AlternativeAllocationDelta(
            baseline_total_value="1000.00",
            alternative_total_value="1000.00",
        ),
        cash_delta=AlternativeCashDelta(
            currency="USD",
            baseline_cash="100.00",
            alternative_cash="120.00",
            base_currency_cash_delta="20.00",
        ),
        currency_delta=AlternativeCurrencyDelta(
            base_currency="USD",
            baseline_weight="1",
            alternative_weight="1",
        ),
        cost_delta=AlternativeCostDelta(status="NOT_AVAILABLE"),
    )
    ranking = AlternativeRankingProjection(
        ranking_reason_codes=["STATUS_FEASIBLE"],
        comparator_inputs=AlternativeComparatorInputs(
            status_priority=0,
            decision_status="READY_FOR_CLIENT_REVIEW",
            approval_count=0,
            blocking_approval_count=0,
            missing_evidence_count=0,
            turnover_trade_count=1,
            objective_rank=0,
        ),
    )

    assert summary.approval_delta.delta == -1
    assert str(summary.risk_delta.top_position_weight_delta_improvement) == "0.20"
    assert ranking.comparator_inputs.status_priority == 0


def test_alternative_typed_contracts_reject_invalid_delta_shapes():
    with pytest.raises(ValidationError):
        AlternativeApprovalDelta(
            baseline_approval_count=-1,
            alternative_approval_count=0,
            delta=1,
        )

    with pytest.raises(ValidationError):
        AlternativeComparatorInputs(
            status_priority=-1,
            decision_status="READY_FOR_CLIENT_REVIEW",
            approval_count=0,
            blocking_approval_count=0,
            missing_evidence_count=0,
            turnover_trade_count=1,
            objective_rank=0,
        )


def test_alternatives_models_keep_request_and_response_boundaries_split():
    request_models = {
        ProposalAlternativesConstraints,
        ProposalAlternativesRequest,
    }
    response_models = {
        AlternativeAllocationDelta,
        AlternativeApprovalDelta,
        AlternativeCandidateSeed,
        AlternativeCashDelta,
        AlternativeComparisonSummary,
        AlternativeComparatorInputs,
        AlternativeConstraintResult,
        AlternativeCostDelta,
        AlternativeCurrencyDelta,
        AlternativeDecisionApprovalRequirementSnapshot,
        AlternativeDecisionMissingEvidenceSnapshot,
        AlternativeDecisionSummarySnapshot,
        AlternativeRankingProjection,
        AlternativeRiskDelta,
        AlternativeTradeoff,
        ProposalAlternative,
        ProposalAlternatives,
        RejectedAlternativeCandidate,
    }

    assert {model.__module__ for model in request_models} == {
        "src.core.advisory.alternatives_request_models"
    }
    assert {model.__module__ for model in response_models} == {
        "src.core.advisory.alternatives_response_models"
    }
