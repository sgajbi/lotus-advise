from copy import deepcopy

import pytest

from src.core.policy_packs import (
    activate_policy_pack_version,
    evaluate_policy_pack_version,
    get_policy_pack_version,
    reset_policy_pack_catalog_for_tests,
    validate_policy_pack_version,
)
from src.core.proposals.exceptions import ProposalValidationError


def setup_function() -> None:
    reset_policy_pack_catalog_for_tests()


def _base_evidence_bundle() -> dict:
    return {
        "context_resolution": {
            "input_mode": "stateful",
            "resolution_source": "LOTUS_CORE",
            "resolved_context": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "as_of": "2026-05-14",
            },
            "advisory_policy_context": {
                "context_source": "LOTUS_CORE",
                "household_id": "HH-PB-001",
                "jurisdiction": "SG",
                "client_classification": "ACCREDITED_INVESTOR",
                "booking_center_code": "SG",
                "account_id": "ACCT-PB-001",
                "time_horizon": "5Y",
                "liquidity_need": "MEDIUM",
                "mandate_id": "MANDATE-BALANCED-001",
                "objectives": ["capital_preservation", "balanced_growth"],
                "restrictions": ["no_single_name_above_10pct"],
            },
        },
        "inputs": {
            "portfolio_snapshot": {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "positions": [{"instrument_id": "US_EQ_ETF", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "50000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "US_EQ_ETF", "price": "100", "currency": "USD"}],
                "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
            },
            "shelf_entries": [
                {
                    "instrument_id": "US_EQ_ETF",
                    "eligibility": {"jurisdictions": ["SG"]},
                    "target_market": {"client_segments": ["ACCREDITED_INVESTOR"]},
                    "complexity": "NON_COMPLEX",
                    "private_asset": False,
                    "structured_product": False,
                }
            ],
            "proposed_trades": [{"instrument_id": "US_EQ_ETF", "side": "BUY"}],
        },
        "risk_lens": {
            "source_service": "lotus-risk",
            "single_position_concentration": {"top_position_weight_current": "0.10"},
            "issuer_concentration": {"hhi_current": "1200"},
            "drawdown": {"max_drawdown_1y": "0.08"},
            "var": {"var_95_1m": "0.04"},
            "stress": {"equity_down_20": "-0.09"},
            "liquidity_risk": {"days_to_liquidate": "3"},
            "private_asset_risk": {"private_asset_weight": "0.00"},
            "climate_geopolitical_risk": {"status": "not_material"},
        },
        "artifact": {
            "assumptions_and_limits": {
                "costs_and_fees": {"included": True, "notes": "Estimated costs captured."},
                "tax": {"included": True, "notes": "Tax review captured."},
                "execution": {"included": True, "notes": "Execution frictions captured."},
            },
            "disclosures": {
                "risk_disclaimer": "Risk disclosure captured.",
                "product_docs": [{"instrument_id": "US_EQ_ETF", "doc_ref": "Factsheet"}],
            },
        },
        "conflict_evidence": {"material_conflict": False, "review_ref": "conflict-review-001"},
    }


def _activate_sg_policy_pack() -> None:
    detail = get_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )
    validate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        requested_by="policy_steward_1",
        idempotency_key="validate-sg-for-evaluation",
        reason={"purpose": "slice 6 evaluation test"},
    )
    activate_policy_pack_version(
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        activated_by="policy_checker_1",
        source_content_hash=detail.policy_pack.content_hash,
        idempotency_key="activate-sg-for-evaluation",
        reason={"purpose": "slice 6 evaluation test"},
    )


def _rule(result, rule_id: str):
    return next(rule for rule in result.rule_results if rule.rule_id == rule_id)


def test_policy_evaluation_ready_path_uses_active_pack_and_source_refs() -> None:
    _activate_sg_policy_pack()

    result = evaluate_policy_pack_version(
        evidence_bundle=_base_evidence_bundle(),
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    assert result.contract_version == "rfc0025.policy-evaluation-engine.v1"
    assert result.evaluation_status == "READY"
    assert result.applicability.status == "APPLICABLE"
    assert result.applicability.matched_selectors["jurisdiction"] == "SG"
    assert result.supportability["policy_evaluation_api"] == "NOT_IMPLEMENTED"
    assert result.supportability["gateway_supported"] is False
    eligibility = _rule(result, "SG_AI_PRODUCT_ELIGIBILITY_REVIEW")
    assert eligibility.status == "READY"
    assert "lotus-core:core_product_eligibility_target_market_complexity" in (
        eligibility.source_authority_refs
    )
    assert _rule(result, "SG_BEST_INTEREST_COST_REVIEW").status == "READY"
    assert _rule(result, "SG_CONFLICT_REVIEW").status == "READY"


def test_policy_evaluation_requires_active_immutable_policy_pack_version() -> None:
    with pytest.raises(ProposalValidationError, match="NOT_ACTIVE"):
        evaluate_policy_pack_version(
            evidence_bundle=_base_evidence_bundle(),
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
        )


def test_policy_evaluation_blocks_missing_source_owner_evidence() -> None:
    evidence = deepcopy(_base_evidence_bundle())
    evidence["inputs"]["shelf_entries"] = []

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="GLOBAL_PRIVATE_BANKING_BASELINE",
        policy_version="2026.05",
    )

    assert result.evaluation_status == "BLOCKED"
    source_rule = _rule(result, "GLOBAL_SOURCE_READINESS_REQUIRED")
    assert source_rule.status == "BLOCKED"
    assert "CORE_PRODUCT_SHELF_NOT_PROVIDED" in source_rule.reason_codes
    assert "RESTORE_SOURCE_OWNER_EVIDENCE" in source_rule.required_actions


def test_policy_evaluation_keeps_degraded_source_evidence_pending_review() -> None:
    evidence = deepcopy(_base_evidence_bundle())
    evidence["risk_lens"]["supportability_state"] = "DEGRADED"

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="GLOBAL_PRIVATE_BANKING_BASELINE",
        policy_version="2026.05",
    )

    assert result.evaluation_status == "PENDING_REVIEW"
    source_rule = _rule(result, "GLOBAL_SOURCE_READINESS_REQUIRED")
    assert source_rule.status == "PENDING_REVIEW"
    assert "RISK_OWNER_POLICY_EVIDENCE_DEGRADED" in source_rule.reason_codes


def test_policy_evaluation_handles_jurisdiction_and_client_segment_applicability() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["context_resolution"]["advisory_policy_context"]["jurisdiction"] = "US"

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    assert result.evaluation_status == "NOT_APPLICABLE"
    assert result.applicability.status == "NOT_APPLICABLE"
    assert result.applicability.reason_codes == ["POLICY_PACK_JURISDICTION_NOT_APPLICABLE"]
    assert result.rule_results == []


def test_policy_evaluation_blocks_applicability_when_client_segment_source_is_missing() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["context_resolution"]["advisory_policy_context"].pop("client_classification")

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    assert result.evaluation_status == "BLOCKED"
    assert result.applicability.status == "BLOCKED"
    assert "client_classification" in result.applicability.missing_evidence


def test_policy_evaluation_marks_complex_products_for_disclosure_and_consent_review() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["inputs"]["shelf_entries"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["inputs"]["shelf_entries"][0]["complexity"] = "COMPLEX"
    evidence["inputs"]["shelf_entries"][0]["structured_product"] = True
    evidence["inputs"]["proposed_trades"][0]["instrument_id"] = "SG_STRUCTURED_NOTE"
    evidence["artifact"]["disclosures"]["product_docs"] = [
        {"instrument_id": "SG_STRUCTURED_NOTE", "doc_ref": "Term sheet"}
    ]

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    complex_rule = _rule(result, "SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW")
    assert result.evaluation_status == "PENDING_REVIEW"
    assert complex_rule.status == "PENDING_REVIEW"
    assert "advisor_reviewed_disclosure:SG_STRUCTURED_NOTE" in complex_rule.missing_evidence
    assert "client_consent:SG_STRUCTURED_NOTE" in complex_rule.missing_evidence
    assert "CAPTURE_CLIENT_CONSENT:SG_STRUCTURED_NOTE" in complex_rule.required_actions


def test_policy_evaluation_blocks_product_ineligible_for_client_segment() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["inputs"]["shelf_entries"][0]["target_market"] = {"client_segments": ["INSTITUTIONAL"]}

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    eligibility = _rule(result, "SG_AI_PRODUCT_ELIGIBILITY_REVIEW")
    assert result.evaluation_status == "BLOCKED"
    assert eligibility.status == "BLOCKED"
    assert "PRODUCT_NOT_IN_TARGET_MARKET_FOR_CLIENT_SEGMENT" in eligibility.reason_codes
    assert "REVIEW_PRODUCT_ELIGIBILITY:US_EQ_ETF" in eligibility.required_actions


def test_policy_evaluation_keeps_best_interest_and_conflicts_pending_without_evidence() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["artifact"]["assumptions_and_limits"]["costs_and_fees"]["included"] = False
    evidence.pop("conflict_evidence")
    evidence["artifact"]["disclosures"]["product_docs"] = []

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    best_interest = _rule(result, "SG_BEST_INTEREST_COST_REVIEW")
    conflicts = _rule(result, "SG_CONFLICT_REVIEW")
    assert result.evaluation_status == "PENDING_REVIEW"
    assert best_interest.status == "PENDING_REVIEW"
    assert "cost_evidence" in best_interest.missing_evidence
    assert "BEST_INTEREST_COST_TAX_FRICTION_EVIDENCE_NOT_MODELED" in (best_interest.reason_codes)
    assert conflicts.status == "PENDING_REVIEW"
    assert "conflict_evidence" in conflicts.missing_evidence
    assert "product_document:US_EQ_ETF" in conflicts.missing_evidence
    assert all(
        "suitable for client-ready use" not in result.outcome.lower()
        for result in result.rule_results
    )


def test_policy_evaluation_blocks_material_conflict_until_supervisory_review() -> None:
    _activate_sg_policy_pack()
    evidence = deepcopy(_base_evidence_bundle())
    evidence["conflict_evidence"]["material_conflict"] = True

    result = evaluate_policy_pack_version(
        evidence_bundle=evidence,
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
    )

    conflicts = _rule(result, "SG_CONFLICT_REVIEW")
    assert result.evaluation_status == "BLOCKED"
    assert conflicts.status == "BLOCKED"
    assert "MATERIAL_CONFLICT_REQUIRES_SUPERVISORY_REVIEW" in conflicts.reason_codes
    assert "SUPERVISORY_CONFLICT_REVIEW" in conflicts.required_actions
