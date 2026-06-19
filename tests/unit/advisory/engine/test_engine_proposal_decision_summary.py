from pathlib import Path

import pytest

from src.core.advisory.decision_summary import build_proposal_decision_summary
from src.core.advisory.decision_summary_models import ProposalDecisionMissingEvidence
from src.core.advisory.decision_summary_status_rules import (
    derive_decision_status,
    recommended_decision_next_action,
)
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


def test_decision_summary_delegates_status_rules_to_focused_module() -> None:
    summary_source = Path("src/core/advisory/decision_summary.py").read_text(encoding="utf-8")
    status_rules_source = Path("src/core/advisory/decision_summary_status_rules.py").read_text(
        encoding="utf-8"
    )

    assert "from src.core.advisory.decision_summary_status_rules import" in summary_source
    assert "def derive_decision_status(" not in summary_source
    assert "def primary_decision_reason_code(" not in summary_source
    assert "def recommended_decision_next_action(" not in summary_source
    assert "def decision_confidence(" not in summary_source
    assert "def derive_decision_status(" in status_rules_source
    assert "def primary_decision_reason_code(" in status_rules_source
    assert "def recommended_decision_next_action(" in status_rules_source
    assert "def decision_confidence(" in status_rules_source


def _missing_evidence(
    reason_code: str, *, blocking: bool = True
) -> ProposalDecisionMissingEvidence:
    return ProposalDecisionMissingEvidence(
        evidence_type="TEST_EVIDENCE",
        reason_code=reason_code,
        summary=f"{reason_code} is unavailable.",
        blocking=blocking,
    )


def _suitability_issue_payload(
    *,
    implication: str,
    issue_id: str = "SUITABILITY_APPROVAL_MAPPING",
    issue_key: str | None = None,
    status_change: str = "NEW",
    classification: str = "NEW",
    details: dict[str, object] | None = None,
) -> dict[str, object]:
    issue_key_value = issue_key or f"APPROVAL_MAPPING|{implication}"
    return {
        "issue_id": issue_id,
        "issue_key": issue_key_value,
        "dimension": "GOVERNANCE",
        "severity": "HIGH",
        "status_change": status_change,
        "classification": classification,
        "summary": "Suitability issue requires approval mapping.",
        "remediation": "Route the proposal through the required approval posture.",
        "approval_implication": implication,
        "details": details or {"approval_implication": implication},
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


def test_decision_next_action_requests_client_context_for_client_evidence_gap() -> None:
    assert (
        recommended_decision_next_action(
            "INSUFFICIENT_EVIDENCE",
            [_missing_evidence("MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE")],
        )
        == "REQUEST_CLIENT_CONTEXT"
    )


@pytest.mark.parametrize(
    ("implication", "expected_approval_type", "expected_blocking"),
    [
        ("COMPLIANCE_REVIEW", "COMPLIANCE_REVIEW", False),
        ("RISK_REVIEW", "RISK_REVIEW", False),
        ("MANDATE_EXCEPTION_APPROVAL", "MANDATE_EXCEPTION_APPROVAL", True),
        ("CLIENT_CONTEXT_REQUIRED", "DATA_REMEDIATION", True),
        ("DATA_REMEDIATION", "DATA_REMEDIATION", True),
    ],
)
def test_decision_summary_maps_suitability_implications_to_approval_requirements(
    implication: str,
    expected_approval_type: str,
    expected_blocking: bool,
) -> None:
    result = _base_result()
    result.gate_decision = None
    result.suitability = SuitabilityResult.model_validate(
        {
            "summary": {
                "new_count": 1,
                "resolved_count": 0,
                "persistent_count": 0,
                "highest_severity_new": "HIGH",
            },
            "issues": [_suitability_issue_payload(implication=implication)],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "COMPLIANCE_REVIEW",
        }
    )

    summary = build_proposal_decision_summary(result)

    assert len(summary.approval_requirements) == 1
    requirement = summary.approval_requirements[0]
    assert requirement.approval_type == expected_approval_type
    assert requirement.blocking_until_approved is expected_blocking
    assert requirement.evidence_refs == [
        f"proposal.suitability.issues.APPROVAL_MAPPING|{implication}"
    ]


@pytest.mark.parametrize(
    ("issue_id", "issue_key", "expected_family", "expected_change_id"),
    [
        (
            "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
            "PRODUCT_COMPLEXITY|STRUCT_NOTE_1",
            "PRODUCT_COMPLEXITY_CHANGE",
            "product-complexity:PRODUCT_COMPLEXITY|STRUCT_NOTE_1",
        ),
        (
            "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE",
            "MANDATE_CONTEXT|RESTRICTED_1",
            "MANDATE_ALIGNMENT_CHANGE",
            "mandate-alignment:MANDATE_CONTEXT|RESTRICTED_1",
        ),
    ],
)
def test_decision_summary_maps_suitability_issues_to_material_changes(
    issue_id: str,
    issue_key: str,
    expected_family: str,
    expected_change_id: str,
) -> None:
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
                _suitability_issue_payload(
                    implication="CLIENT_CONTEXT_REQUIRED",
                    issue_id=issue_id,
                    issue_key=issue_key,
                    classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
                    details={"instrument_id": "STRUCT_NOTE_1"},
                )
            ],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "COMPLIANCE_REVIEW",
        }
    )

    summary = build_proposal_decision_summary(result)

    material_change = next(
        change for change in summary.material_changes if change.family == expected_family
    )
    assert material_change.change_id == expected_change_id
    assert material_change.delta == {"classification": "UNKNOWN_DUE_TO_MISSING_EVIDENCE"}
    assert material_change.evidence_refs == [f"proposal.suitability.issues.{issue_key}"]


def test_decision_next_action_requests_mandate_context_for_mandate_evidence_gap() -> None:
    assert (
        recommended_decision_next_action(
            "INSUFFICIENT_EVIDENCE",
            [_missing_evidence("MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE")],
        )
        == "REQUEST_MANDATE_CONTEXT"
    )


def test_decision_next_action_revises_when_insufficient_evidence_has_no_context_owner() -> None:
    assert (
        recommended_decision_next_action(
            "INSUFFICIENT_EVIDENCE",
            [_missing_evidence("MISSING_RISK_LENS")],
        )
        == "REVISE_PROPOSAL"
    )


def test_decision_status_blocks_before_missing_evidence_or_gate_review() -> None:
    result = _base_result()
    result.status = "BLOCKED"
    result.gate_decision = GateDecision(
        gate="COMPLIANCE_REVIEW_REQUIRED",
        recommended_next_step="COMPLIANCE_REVIEW",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=1,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )

    status = derive_decision_status(result, [_missing_evidence("MISSING_RISK_LENS")])

    assert status == "BLOCKED_REMEDIATION_REQUIRED"


def test_decision_status_requires_evidence_before_gate_review() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = GateDecision(
        gate="COMPLIANCE_REVIEW_REQUIRED",
        recommended_next_step="COMPLIANCE_REVIEW",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=1,
            new_high_suitability_count=1,
            new_medium_suitability_count=0,
        ),
    )

    status = derive_decision_status(result, [_missing_evidence("MISSING_RISK_LENS")])

    assert status == "INSUFFICIENT_EVIDENCE"


def test_decision_status_uses_gate_review_when_evidence_is_non_blocking() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = GateDecision(
        gate="RISK_REVIEW_REQUIRED",
        recommended_next_step="RISK_REVIEW",
        reasons=[],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=1,
            new_high_suitability_count=0,
            new_medium_suitability_count=1,
        ),
    )

    status = derive_decision_status(
        result,
        [_missing_evidence("MISSING_OPTIONAL_RISK_DETAIL", blocking=False)],
    )

    assert status == "REQUIRES_RISK_REVIEW"


def test_decision_status_recommends_revision_for_pending_review_without_gate() -> None:
    result = _base_result()
    result.status = "PENDING_REVIEW"
    result.gate_decision = None

    status = derive_decision_status(result, [])

    assert status == "REVISION_RECOMMENDED"


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


def test_decision_summary_blocks_client_progression_when_ready_proposal_lacks_risk_lens() -> None:
    result = _base_result()
    result.status = "READY"
    result.gate_decision = GateDecision(
        gate="CLIENT_CONSENT_REQUIRED",
        recommended_next_step="REQUEST_CLIENT_CONSENT",
        reasons=[
            GateReason(
                reason_code="CLIENT_CONSENT_REQUIRED",
                severity="MEDIUM",
                source="RULE_ENGINE",
                details={"consent_type": "execution_progression"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=0,
            soft_fail_count=0,
            new_high_suitability_count=0,
            new_medium_suitability_count=0,
        ),
    )
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "unavailable",
        "degraded": True,
        "degraded_reasons": ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"],
    }

    summary = build_proposal_decision_summary(result)

    assert summary.decision_status == "INSUFFICIENT_EVIDENCE"
    assert summary.primary_reason_code == "MISSING_RISK_LENS"
    assert summary.recommended_next_action == "REVISE_PROPOSAL"
    assert summary.confidence == "LOW"
    assert summary.missing_evidence[0].blocking is True


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


def test_decision_summary_preserves_combined_missing_evidence_order_and_blocking() -> None:
    result = _base_result()
    result.status = "BLOCKED"
    result.diagnostics.data_quality["price_missing"].append("EQ_1")
    result.diagnostics.data_quality["fx_missing"].append("EUR/USD")
    result.explanation["authority_resolution"] = {
        "simulation_authority": "lotus_core",
        "risk_authority": "unavailable",
        "degraded": True,
        "degraded_reasons": ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"],
    }
    result.suitability = SuitabilityResult.model_validate(
        {
            "summary": {
                "new_count": 2,
                "resolved_count": 0,
                "persistent_count": 0,
                "highest_severity_new": "HIGH",
            },
            "issues": [
                {
                    "issue_id": "MISSING_SUITABILITY_MARKET_PRICE",
                    "issue_key": "DATA_QUALITY|EQ_1",
                    "dimension": "DATA_QUALITY",
                    "severity": "HIGH",
                    "status_change": "NEW",
                    "classification": "NEW",
                    "summary": "Market price evidence is incomplete.",
                    "remediation": "Attach required market price evidence.",
                    "approval_implication": "DATA_REMEDIATION",
                    "details": {"instrument_id": "EQ_1"},
                    "evidence": {
                        "as_of": "md_test",
                        "snapshot_ids": {
                            "portfolio_snapshot_id": "pf_decision_001",
                            "market_data_snapshot_id": "md_test",
                        },
                    },
                    "policy_pack_id": "global-private-banking-baseline",
                    "policy_version": "enterprise-suitability-policy.2026-04",
                },
                {
                    "issue_id": "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
                    "issue_key": "PRODUCT_COMPLEXITY|STRUCT_NOTE_1",
                    "dimension": "PRODUCT",
                    "severity": "MEDIUM",
                    "status_change": "NEW",
                    "classification": "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
                    "summary": "Complex product evidence is incomplete.",
                    "remediation": "Capture client product-complexity evidence.",
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
                },
            ],
            "policy_pack_id": "global-private-banking-baseline",
            "policy_version": "enterprise-suitability-policy.2026-04",
            "recommended_gate": "COMPLIANCE_REVIEW",
        }
    )

    summary = build_proposal_decision_summary(result)

    assert [item.reason_code for item in summary.missing_evidence] == [
        "MISSING_REQUIRED_MARKET_PRICE",
        "MISSING_REQUIRED_FX_DATA",
        "MISSING_RISK_LENS",
        "MISSING_SUITABILITY_MARKET_PRICE",
        "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
    ]
    assert [item.blocking for item in summary.missing_evidence] == [
        True,
        True,
        True,
        True,
        True,
    ]
    assert summary.missing_evidence[-2].evidence_refs == [
        "proposal.suitability.issues.DATA_QUALITY|EQ_1"
    ]
    assert summary.missing_evidence[-1].evidence_type == "SUITABILITY_CONTEXT"


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


def test_decision_summary_evidence_refs_are_sorted_unique_and_complete() -> None:
    result = _base_result()
    result.status = "BLOCKED"
    result.diagnostics.data_quality["price_missing"].append("EQ_1")
    result.explanation["advisory_policy_context"] = {
        "client_context_status": "AVAILABLE",
        "mandate_context_status": "AVAILABLE",
    }
    result.gate_decision = GateDecision(
        gate="BLOCKED",
        recommended_next_step="FIX_INPUT",
        reasons=[
            GateReason(
                reason_code="DATA_QUALITY_MISSING_PRICE",
                severity="HIGH",
                source="DATA_QUALITY",
                details={"instrument_id": "EQ_1"},
            )
        ],
        summary=GateDecisionSummary(
            hard_fail_count=1,
            soft_fail_count=0,
            new_high_suitability_count=0,
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
                    "issue_key": "PRODUCT_COMPLEXITY|ALT_1",
                    "dimension": "PRODUCT",
                    "severity": "HIGH",
                    "status_change": "NEW",
                    "classification": "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
                    "summary": "Complex product evidence is missing.",
                    "remediation": "Capture client context for the complex product.",
                    "approval_implication": "CLIENT_CONTEXT_REQUIRED",
                    "details": {"product_type": "STRUCTURED_NOTE"},
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

    assert summary.evidence_refs == [
        "proposal.diagnostics.data_quality.price_missing",
        "proposal.explanation.advisory_policy_context",
        "proposal.explanation.authority_resolution",
        "proposal.gate_decision",
        "proposal.status",
        "proposal.suitability",
        "proposal.suitability.issues.PRODUCT_COMPLEXITY|ALT_1",
    ]


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
