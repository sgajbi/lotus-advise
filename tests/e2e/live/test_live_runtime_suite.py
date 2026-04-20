import os

import pytest

from scripts.validate_live_runtime_suite import validate_live_runtime_suite


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_RUNTIME_SUITE") != "1",
    reason="set RUN_LIVE_RUNTIME_SUITE=1 to run the sequential live runtime suite",
)
def test_live_runtime_suite():
    result = validate_live_runtime_suite()

    assert result.parity.complete_issuer_portfolio
    assert result.parity.lifecycle_current_state == "EXECUTED"
    assert result.parity.review_decision.decision_status in {
        "REQUIRES_RISK_REVIEW",
        "REQUIRES_COMPLIANCE_REVIEW",
    }
    assert (
        result.parity.noop_alternatives.feasible_count
        + result.parity.noop_alternatives.feasible_with_review_count
        >= 3
    )
    assert result.parity.concentration_alternatives.top_ranked_objective == "REDUCE_CONCENTRATION"
    assert result.parity.cash_raise_alternatives.top_ranked_objective == "RAISE_CASH"
    assert (
        result.parity.cross_currency_alternatives.top_ranked_objective
        == "IMPROVE_CURRENCY_ALIGNMENT"
    )
    assert (
        "ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"
        in result.parity.restricted_product_alternatives.rejected_reason_codes
    )
    assert result.parity.workspace_rationale_initial_run_id
    assert result.parity.workspace_rationale_replacement_run_id
    assert result.parity.workspace_rationale_review_state == "SUPERSEDED"
    assert result.parity.workspace_rationale_supportability_status == "HISTORICAL"
    assert result.degraded.risk_degraded_reason == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    assert result.degraded.core_degraded_reason == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    assert result.degraded.fallback_mode == "NONE"
    assert result.degraded.insufficient_evidence_decision.decision_status == "INSUFFICIENT_EVIDENCE"
    assert (
        "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"
        in result.degraded.risk_unavailable_alternatives.rejected_reason_codes
    )
    assert (
        "LOTUS_CORE_SIMULATION_UNAVAILABLE"
        in result.degraded.core_unavailable_alternatives.rejected_reason_codes
    )
