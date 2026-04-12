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
    ProposedTrade,
    ShelfEntry,
    SuitabilityResult,
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
    result.suitability = SuitabilityResult.model_validate(
        {
            "summary": {
                "new_count": 0,
                "resolved_count": 0,
                "persistent_count": 0,
                "highest_severity_new": None,
            },
            "issues": [],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "NONE",
        }
    )
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
    assert summary.material_changes == []


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
    assert any(
        change.family == "APPROVAL_REQUIREMENT_CHANGE" for change in summary.material_changes
    )


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


def test_decision_summary_projects_insufficient_evidence_for_complex_product_context_gap() -> None:
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
                details={"issue_key": "PRODUCT_COMPLEXITY|STRUCT_NOTE_1"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=1,
            new_medium_suitability_count=0,
        ),
    )
    result.suitability = SuitabilityResult.model_validate(
        {
            "summary": {
                "new_count": 1,
                "resolved_count": 0,
                "persistent_count": 0,
                "highest_severity_new": "HIGH",
            },
            "issues": [
                {
                    "issue_id": "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
                    "issue_key": "PRODUCT_COMPLEXITY|STRUCT_NOTE_1",
                    "dimension": "PRODUCT",
                    "severity": "HIGH",
                    "status_change": "NEW",
                    "classification": "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
                    "summary": "Complex product evidence is incomplete.",
                    "remediation": "Capture client product-complexity evidence before proceeding.",
                    "approval_implication": "CLIENT_CONTEXT_REQUIRED",
                    "details": {"instrument_id": "STRUCT_NOTE_1"},
                    "evidence": {
                        "as_of": "md_test",
                        "snapshot_ids": {
                            "portfolio_snapshot_id": "pf_decision_001",
                            "market_data_snapshot_id": "md_test",
                        },
                    },
                    "policy_pack_id": "global-private-banking-baseline",
                    "policy_version": "enterprise-suitability-policy.2026-04",
                }
            ],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "COMPLIANCE_REVIEW",
        }
    )

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "INSUFFICIENT_EVIDENCE"
    assert summary.primary_reason_code == "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE"
    assert summary.suitability_policy_version == "enterprise-suitability-policy.2026-04"
    assert summary.missing_evidence[0].reason_code == "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE"


def test_decision_summary_projects_available_client_and_mandate_posture() -> None:
    result = _base_result()
    result.explanation["advisory_policy_context"] = {
        "client_context_status": "AVAILABLE",
        "mandate_context_status": "AVAILABLE",
    }

    summary = build_proposal_decision_summary(result)

    assert summary.client_and_mandate_posture is not None
    assert summary.client_and_mandate_posture.status == "AVAILABLE"
    assert "advisory_policy_context" in " ".join(summary.evidence_refs)


def test_decision_summary_projects_currency_exposure_change_for_cross_currency_trade() -> None:
    result = run_proposal_simulation(
        portfolio=PortfolioSnapshot(
            portfolio_id="pf_decision_fx_001",
            base_currency="USD",
            positions=[],
            cash_balances=[{"currency": "USD", "amount": "1000"}],
        ),
        market_data=MarketDataSnapshot(
            prices=[Price(instrument_id="EUR_EQ_1", price="100", currency="EUR")],
            fx_rates=[{"pair": "EUR/USD", "rate": "1.2"}],
        ),
        shelf=[
            ShelfEntry(
                instrument_id="EUR_EQ_1",
                status="APPROVED",
                issuer_id="ISS_EUR_1",
                liquidity_tier="L1",
            )
        ],
        options=EngineOptions(enable_proposal_simulation=True),
        proposed_cash_flows=[],
        proposed_trades=[ProposedTrade(side="BUY", instrument_id="EUR_EQ_1", quantity="1")],
        request_hash="sha256:fx",
        correlation_id="corr_fx",
    )
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "lotus_risk",
        "degraded": False,
        "degraded_reasons": [],
    }

    summary = build_proposal_decision_summary(result)

    assert any(change.family == "CURRENCY_EXPOSURE_CHANGE" for change in summary.material_changes)


def test_decision_summary_projects_concentration_change_from_risk_lens() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = GateDecision(
        gate="RISK_REVIEW_REQUIRED",
        recommended_next_step="RISK_REVIEW",
        reasons=[
            GateReason(
                reason_code="NEW_MEDIUM_SUITABILITY_ISSUE",
                severity="MEDIUM",
                source="SUITABILITY",
                details={"issue_key": "SINGLE_POSITION_MAX|EQ_1"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=1,
        ),
    )
    result.explanation["risk_lens"] = {
        "source_service": "lotus-risk",
        "single_position_concentration": {
            "top_position_weight_current": 0.20,
            "top_position_weight_proposed": 0.27,
            "top_position_weight_delta": 0.07,
        },
        "issuer_concentration": {
            "hhi_current": 1200,
            "hhi_proposed": 1850,
            "hhi_delta": 650,
        },
    }

    summary = build_proposal_decision_summary(result)

    assert any(change.family == "CONCENTRATION_CHANGE" for change in summary.material_changes)
    assert any(req.approval_type == "RISK_REVIEW" for req in summary.approval_requirements)


def test_decision_summary_projects_mandate_alignment_change_and_exception_requirement() -> None:
    result = _base_result()
    result.suitability = SuitabilityResult.model_validate(
        {
            "summary": {
                "new_count": 1,
                "resolved_count": 0,
                "persistent_count": 0,
                "highest_severity_new": "HIGH",
            },
            "issues": [
                {
                    "issue_id": "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE",
                    "issue_key": "MANDATE_CONTEXT|RESTRICTED_1",
                    "dimension": "PRODUCT",
                    "severity": "HIGH",
                    "status_change": "NEW",
                    "classification": "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
                    "summary": "Restricted product requires mandate context before recommendation.",
                    "remediation": (
                        "Capture mandate context for the restricted-product recommendation."
                    ),
                    "approval_implication": "MANDATE_EXCEPTION_APPROVAL",
                    "details": {"instrument_id": "RESTRICTED_1"},
                    "evidence": {
                        "as_of": "md_test",
                        "snapshot_ids": {
                            "portfolio_snapshot_id": "pf_decision_001",
                            "market_data_snapshot_id": "md_test",
                        },
                    },
                    "policy_pack_id": "global-private-banking-baseline",
                    "policy_version": "enterprise-suitability-policy.2026-04",
                }
            ],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "COMPLIANCE_REVIEW",
        }
    )

    summary = build_proposal_decision_summary(result)

    assert any(change.family == "MANDATE_ALIGNMENT_CHANGE" for change in summary.material_changes)
    assert any(
        req.approval_type == "MANDATE_EXCEPTION_APPROVAL" for req in summary.approval_requirements
    )
