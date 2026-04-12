import pytest
from pydantic import ValidationError

from src.core.advisory import (
    ProposalAlternative,
    ProposalAlternativesConstraints,
    ProposalAlternativesRequest,
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
