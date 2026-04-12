from src.core.advisory.decision_summary import build_proposal_decision_summary
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import (
    EngineOptions,
    GateDecision,
    GateDecisionSummary,
    GateReason,
    MarketDataSnapshot,
    PortfolioSnapshot,
    Price,
    ProposalResult,
    ShelfEntry,
)


def _base_result() -> ProposalResult:
    result = run_proposal_simulation(
        portfolio=PortfolioSnapshot(
            portfolio_id="pf_decision_001",
            base_currency="USD",
            positions=[],
            cash_balances=[],
        ),
        market_data=MarketDataSnapshot(
            prices=[Price(instrument_id="EQ_1", price="100", currency="USD")],
            fx_rates=[],
        ),
        shelf=[ShelfEntry(instrument_id="EQ_1", status="APPROVED")],
        options=EngineOptions(enable_proposal_simulation=True),
        proposed_cash_flows=[],
        proposed_trades=[],
        request_hash="sha256:test",
        correlation_id="corr_test",
    )
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "lotus_risk",
        "degraded": False,
        "degraded_reasons": [],
    }
    return result


def test_decision_summary_projects_ready_for_client_review() -> None:
    result = _base_result()
    result.gate_decision = GateDecision(
        gate="EXECUTION_READY",
        recommended_next_step="EXECUTE",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "READY_FOR_CLIENT_REVIEW"
    assert summary.top_level_status == "READY"
    assert summary.recommended_next_action == "DISCUSS_WITH_CLIENT"
    assert summary.confidence == "HIGH"


def test_decision_summary_projects_compliance_review_from_gate() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = GateDecision(
        gate="COMPLIANCE_REVIEW_REQUIRED",
        recommended_next_step="COMPLIANCE_REVIEW",
        reasons=[
            GateReason(
                reason_code="NEW_HIGH_SUITABILITY_ISSUE",
                severity="HIGH",
                source="SUITABILITY",
                details={"issue_key": "ISSUER_MAX|ISS_1"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=1,
            new_medium_suitability_count=0,
        ),
    )

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "REQUIRES_COMPLIANCE_REVIEW"
    assert summary.primary_reason_code == "NEW_HIGH_SUITABILITY_ISSUE"
    assert summary.recommended_next_action == "REVIEW_COMPLIANCE"
    assert summary.approval_requirements[0].approval_type == "COMPLIANCE_REVIEW"


def test_decision_summary_projects_blocked_remediation_for_blocked_status() -> None:
    result = _base_result()
    result.status = "BLOCKED"
    result.gate_decision = GateDecision(
        gate="BLOCKED",
        recommended_next_step="FIX_INPUT",
        reasons=[
            GateReason(
                reason_code="DATA_QUALITY_MISSING_PRICE",
                severity="HIGH",
                source="DATA_QUALITY",
                details={"count": "1"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=1,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )
    result.diagnostics.data_quality["price_missing"].append("EQ_1")

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "BLOCKED_REMEDIATION_REQUIRED"
    assert summary.recommended_next_action == "FIX_INPUT"
    assert summary.confidence == "INSUFFICIENT"
    assert summary.approval_requirements[0].approval_type == "DATA_REMEDIATION"


def test_decision_summary_projects_insufficient_evidence_when_review_state_has_missing_risk() -> (
    None
):
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = None
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "unavailable",
        "degraded": True,
        "degraded_reasons": ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"],
    }

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "INSUFFICIENT_EVIDENCE"
    assert summary.primary_reason_code == "MISSING_RISK_LENS"
    assert summary.confidence == "LOW"
    assert summary.missing_evidence[0].reason_code == "MISSING_RISK_LENS"


def test_decision_summary_projects_revision_recommended_without_gate() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = None

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "REVISION_RECOMMENDED"
    assert summary.primary_reason_code == "PROPOSAL_REVISION_RECOMMENDED"
    assert summary.recommended_next_action == "REVISE_PROPOSAL"
