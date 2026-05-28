from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    BackendRuntimePosture,
    RuntimeEndpointEvidence,
    build_backend_proof_capture,
    build_default_scenario_contract,
    build_journey_integration_proof_summary,
    default_capture_metadata,
    review_material_fields,
    sanitize_live_runtime_summary,
)


def _live_runtime_payload() -> dict:
    return {
        "parity": {
            "complete_issuer_portfolio": RFC28_CANONICAL_PORTFOLIO_ID,
            "lifecycle_current_state": "EXECUTED",
            "lifecycle_latest_version_no": 2,
            "async_lifecycle_current_state": "EXECUTED",
            "async_lifecycle_latest_version_no": 2,
            "execution_handoff_status": "REQUESTED",
            "execution_terminal_status": "EXECUTED",
            "report_status": "READY",
            "workspace_rationale_initial_run_id": "packrun_initial",
            "workspace_rationale_replacement_run_id": "packrun_replacement",
            "workspace_rationale_review_state": "SUPERSEDED",
            "workspace_rationale_supportability_status": "HISTORICAL",
            "proposal_narrative": {
                "generation_mode": "DETERMINISTIC_TEMPLATE",
                "policy_status": "READY_FOR_ADVISOR_REVIEW",
                "read_posture_source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
                "regeneration_persistence_status": "NOT_PERSISTED_REVIEW_REQUIRED",
                "review_state": "APPROVED_FOR_ADVISOR_USE",
                "client_ready_status": "NOT_REQUESTED",
                "source_narrative_hash": "sha256:source-narrative",
                "report_status": "READY",
                "report_package_status": "INCLUDED_REVIEWED_NARRATIVE",
                "guardrail_failure_status": "LOCAL_POLICY_REPRODUCED",
                "ai_assisted_status": "NOT_REQUESTED",
            },
            "proposal_memo": {
                "memo_status": "BLOCKED",
                "lifecycle_status": "DRAFT",
                "memo_hash": "sha256:memo",
                "source_input_hash": "sha256:source",
                "projection_client_ready_publication": "BLOCKED",
                "review_action": "APPROVE_FOR_ADVISOR_USE",
                "review_client_ready_publication": "BLOCKED",
                "report_status": "READY",
                "report_package_status": "ARCHIVED",
                "requested_output_formats": ["pdf"],
                "render_ref_status": "RECORDED",
                "archive_ref_status": "RECORDED",
                "archive_retention_posture": "OWNED_BY_LOTUS_ARCHIVE",
                "archive_legal_hold_posture": "OWNED_BY_LOTUS_ARCHIVE",
                "archive_access_audit_ref_status": "RECORDED",
                "ai_status": "UNAVAILABLE",
                "ai_authoritative_for_memo_status": False,
                "ai_review_required": True,
                "lineage_complete": True,
                "replay_client_ready_publication": "BLOCKED",
                "stale_hash_block_status": "MEMO_HASH_MISMATCH",
                "client_ready_release_block_status": "MEMO_CLIENT_READY_RELEASE_NOT_SUPPORTED",
                "client_ready_document_block_status": "MEMO_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
            },
            "proposal_policy": {
                "policy_pack_id": "SG_PRIVATE_BANKING_REFERENCE",
                "policy_version": "2026.05",
                "evaluation_status": "PENDING_REVIEW",
                "material_rule_count": 6,
                "pending_rule_count": 3,
                "approval_dependency_count": 1,
                "disclosure_requirement_count": 1,
                "consent_requirement_count": 1,
                "source_ref_count": 8,
                "source_gap_count": 0,
                "workflow_sign_off_status": "PENDING_REVIEW",
                "workflow_client_ready_publication": "BLOCKED",
                "workflow_open_requirement_count": 3,
                "sign_off_decision_status": "SIGNED_OFF",
                "report_status": "READY",
                "report_package_status": "ARCHIVED",
                "requested_output_formats": ["pdf"],
                "render_ref_status": "RECORDED",
                "archive_ref_status": "RECORDED",
                "archive_retention_posture": "OWNED_BY_LOTUS_ARCHIVE",
                "archive_legal_hold_posture": "OWNED_BY_LOTUS_ARCHIVE",
                "archive_access_audit_ref_status": "RECORDED",
                "ai_status": "UNAVAILABLE",
                "ai_authoritative_for_policy_status": False,
                "ai_human_review_required": True,
                "ai_raw_source_evidence_included": False,
                "lineage_complete": True,
                "replay_evaluation_hash_matches": True,
                "replay_source_evidence_hash_matches": True,
                "stale_hash_block_status": "POLICY_EVALUATION_HASH_MISMATCH",
                "client_ready_document_block_status": "POLICY_CLIENT_READY_DOCUMENT_NOT_SUPPORTED",
                "forbidden_ai_action_block_status": "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION",
            },
            "ready_decision": {
                "top_level_status": "READY",
                "decision_status": "REQUIRES_CLIENT_CONSENT",
                "primary_reason_code": "CLIENT_CONSENT_REQUIRED",
                "recommended_next_action": "DISCUSS_WITH_CLIENT",
                "approval_requirement_types": ["CLIENT_CONSENT"],
            },
            "review_decision": {
                "top_level_status": "READY",
                "decision_status": "REQUIRES_RISK_REVIEW",
                "primary_reason_code": "NEW_MEDIUM_SUITABILITY_ISSUE",
                "recommended_next_action": "REVIEW_RISK",
                "approval_requirement_types": ["RISK_REVIEW"],
            },
            "blocked_decision": {
                "top_level_status": "BLOCKED",
                "decision_status": "BLOCKED_REMEDIATION_REQUIRED",
                "primary_reason_code": "DATA_QUALITY_MISSING_FX",
                "recommended_next_action": "FIX_INPUT",
                "approval_requirement_types": ["DATA_REMEDIATION"],
            },
            "noop_alternatives": {
                "requested_objectives": ["REDUCE_CONCENTRATION", "RAISE_CASH"],
                "feasible_count": 2,
                "feasible_with_review_count": 1,
                "rejected_count": 1,
                "selected_alternative_id": None,
                "selected_rank": None,
                "top_ranked_objective": "REDUCE_CONCENTRATION",
                "top_ranked_reason_codes": ["STATUS_FEASIBLE"],
                "rejected_reason_codes": ["ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"],
            },
            "concentration_alternatives": {
                "requested_objectives": ["REDUCE_CONCENTRATION"],
                "feasible_count": 1,
                "feasible_with_review_count": 0,
                "rejected_count": 0,
                "selected_alternative_id": None,
                "selected_rank": None,
                "top_ranked_objective": "REDUCE_CONCENTRATION",
                "top_ranked_reason_codes": ["STATUS_FEASIBLE"],
                "rejected_reason_codes": [],
            },
            "cash_raise_alternatives": {
                "requested_objectives": ["RAISE_CASH"],
                "feasible_count": 1,
                "feasible_with_review_count": 0,
                "rejected_count": 0,
                "selected_alternative_id": None,
                "selected_rank": None,
                "top_ranked_objective": "RAISE_CASH",
                "top_ranked_reason_codes": ["STATUS_FEASIBLE"],
                "rejected_reason_codes": [],
            },
            "cross_currency_alternatives": {
                "requested_objectives": ["IMPROVE_CURRENCY_ALIGNMENT"],
                "feasible_count": 1,
                "feasible_with_review_count": 0,
                "rejected_count": 0,
                "selected_alternative_id": None,
                "selected_rank": None,
                "top_ranked_objective": "IMPROVE_CURRENCY_ALIGNMENT",
                "top_ranked_reason_codes": ["STATUS_FEASIBLE"],
                "rejected_reason_codes": [],
            },
            "restricted_product_alternatives": {
                "requested_objectives": ["AVOID_RESTRICTED_PRODUCTS"],
                "feasible_count": 0,
                "feasible_with_review_count": 0,
                "rejected_count": 1,
                "selected_alternative_id": None,
                "selected_rank": None,
                "top_ranked_objective": None,
                "top_ranked_reason_codes": [],
                "rejected_reason_codes": ["ALTERNATIVE_OBJECTIVE_PENDING_CANONICAL_EVIDENCE"],
            },
        },
        "degraded": {
            "risk_drill_portfolio": RFC28_CANONICAL_PORTFOLIO_ID,
            "risk_degraded_reason": "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
            "core_degraded_reason": "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
            "fallback_mode": "NONE",
            "insufficient_evidence_decision": {
                "top_level_status": "READY",
                "decision_status": "INSUFFICIENT_EVIDENCE",
                "primary_reason_code": "MISSING_RISK_LENS",
                "recommended_next_action": "REVIEW_RISK",
            },
            "risk_unavailable_alternatives": {
                "requested_objectives": ["REDUCE_CONCENTRATION"],
                "rejected_count": 1,
                "rejected_reason_codes": ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"],
            },
            "core_unavailable_alternatives": {
                "requested_objectives": ["RAISE_CASH"],
                "rejected_count": 1,
                "rejected_reason_codes": ["LOTUS_CORE_SIMULATION_UNAVAILABLE"],
            },
        },
    }


def _runtime_posture() -> BackendRuntimePosture:
    return BackendRuntimePosture(
        base_url="http://advise.dev.lotus",
        environment="local",
        endpoints=[
            RuntimeEndpointEvidence(
                endpoint="/health/ready",
                http_status=200,
                posture="READY",
                summary={"status": "ready"},
            ),
            RuntimeEndpointEvidence(
                endpoint="/platform/capabilities",
                http_status=200,
                posture="READY",
                summary={
                    "feature_keys": ["advisory.proposals.lifecycle"],
                    "workflow_keys": ["advisory_proposal_lifecycle"],
                    "operational_ready": True,
                    "degraded": False,
                    "degraded_reasons": [],
                },
            ),
        ],
    )


def _metadata():
    return default_capture_metadata(
        repository_sha="abc123",
        service_version="0.1.0",
        environment="local",
        correlation_id="corr-rfc0028-backend-proof",
        generated_at=datetime(2026, 5, 28, 9, 30, tzinfo=UTC),
        live_suite_result_ref="output/rfc0028/source/result.json",
    )


def test_sanitized_runtime_summary_keeps_proof_fields_without_raw_hash_payloads() -> None:
    summary = sanitize_live_runtime_summary(_live_runtime_payload())

    assert summary["scenario_id"] == "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL"
    assert summary["primary_portfolio_id"] == RFC28_CANONICAL_PORTFOLIO_ID
    assert summary["proposal_lifecycle"]["execution_terminal_status"] == "EXECUTED"
    assert summary["proposal_narrative"]["review_state"] == "APPROVED_FOR_ADVISOR_USE"
    assert summary["proposal_memo"]["review_client_ready_publication"] == "BLOCKED"
    assert summary["proposal_policy"]["evaluation_status"] == "PENDING_REVIEW"
    assert summary["degraded_runtime"]["core_degraded_reason"] == (
        "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    )
    serialized = repr(summary)
    assert "sha256:memo" not in serialized
    assert "sha256:source-narrative" not in serialized


def test_material_field_review_blocks_claim_drift_at_lowest_layer() -> None:
    reviews = review_material_fields(_live_runtime_payload())

    assert {review.review_posture for review in reviews} == {"PASS"}
    assert any(
        review.source_path == "parity.proposal_policy.evaluation_status" for review in reviews
    )
    assert any(
        review.source_path == "parity.proposal_policy.ai_raw_source_evidence_included"
        and review.expected_posture == "False"
        for review in reviews
    )

    drifted = _live_runtime_payload()
    drifted["parity"]["proposal_policy"]["workflow_client_ready_publication"] = "APPROVED"
    with pytest.raises(ValueError, match="MATERIAL_REVIEW_BLOCKED"):
        build_backend_proof_capture(
            drifted,
            metadata=_metadata(),
            runtime_posture=_runtime_posture(),
        )


def test_journey_integration_proof_blocks_ai_policy_and_cockpit_overclaims() -> None:
    summary = build_journey_integration_proof_summary(_live_runtime_payload())

    assert summary.required_workbench_panels == [
        "advisory.advisor_cockpit",
        "advisory.suitability_review",
        "proposal.memo_evidence_pack",
        "advisory.bank_demo_proof",
    ]
    assert summary.policy_evidence.policy_pack_id == "SG_PRIVATE_BANKING_REFERENCE"
    assert summary.policy_evidence.client_ready_publication == "BLOCKED"
    assert summary.cockpit_evidence.required_workbench_panel == "advisory.advisor_cockpit"
    ai_rows = {row.evidence_family: row for row in summary.ai_model_risk_controls}
    assert ai_rows["PROPOSAL_MEMO"].authoritative_for_advice is False
    assert ai_rows["PROPOSAL_MEMO"].human_review_required is True
    assert ai_rows["POLICY_EVIDENCE"].raw_source_evidence_included is False
    assert ai_rows["ADVISORY_COPILOT"].proof_posture == "NOT_PROBED"
    assert "Raw prompts" in summary.unsupported_claims[1]

    drifted = _live_runtime_payload()
    drifted["parity"]["proposal_policy"]["ai_raw_source_evidence_included"] = True
    with pytest.raises(ValueError, match="raw prompts or raw source evidence"):
        build_journey_integration_proof_summary(drifted)


def test_scenario_contract_uses_governed_workbench_panel_identifiers() -> None:
    scenario = build_default_scenario_contract()
    panel_refs = {panel for step in scenario.steps for panel in step.required_workbench_panels}

    assert "advisory.advisor_cockpit" in panel_refs
    assert "proposal.memo_evidence_pack" in panel_refs
    assert "advisory.suitability_review" in panel_refs
    assert "advisor_cockpit" not in panel_refs


def test_backend_proof_capture_builds_claim_register_and_blocked_proof_pack() -> None:
    bundle = build_backend_proof_capture(
        _live_runtime_payload(),
        metadata=_metadata(),
        runtime_posture=_runtime_posture(),
    )

    assert bundle.proof_pack.proof_marker == RFC28_CANONICAL_PROOF_MARKER
    assert bundle.proof_pack.client_ready_posture == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert "RFC0028_BACKEND_MATERIAL_FIELD_REVIEW_PASSED" in bundle.proof_pack.evidence_markers
    assert "RFC0028_DOCUMENT_PROOF_SUMMARY_CREATED" in bundle.proof_pack.evidence_markers
    assert "RFC0028_JOURNEY_INTEGRATION_PROOF_CREATED" in bundle.proof_pack.evidence_markers
    assert "RFC0028_COMMERCIAL_MATERIAL_PACK_CREATED" in bundle.proof_pack.evidence_markers
    assert "RFC0028_RUNTIME_POSTURE_CAPTURED" in bundle.proof_pack.evidence_markers
    assert "RFC0028_RUNTIME_SECURITY_POSTURE_HARDENED" in bundle.proof_pack.evidence_markers
    assert bundle.proof_pack.repository_shas == {"lotus-advise": "abc123"}
    commit_allowed_assets = {
        asset.asset_id for asset in bundle.proof_pack.assets if asset.commit_allowed
    }
    assert commit_allowed_assets == {"commercial_material_pack"}
    assert any(
        asset.asset_id == "journey_integration_proof_summary"
        and asset.asset_type == "GOVERNANCE_INTEGRATION_SUMMARY"
        for asset in bundle.proof_pack.assets
    )
    assert any(
        asset.asset_id == "commercial_material_pack"
        and asset.asset_type == "COMMERCIAL_DOCUMENT"
        and asset.access_class == "CUSTOMER_CONSUMABLE_SUMMARY"
        for asset in bundle.proof_pack.assets
    )
    claim_postures = {
        claim.claim_id: claim.classification for claim in bundle.supported_claim_register.claims
    }
    assert claim_postures["backend_proof_capture_repeatable"] == "IMPLEMENTATION_BACKED"
    assert (
        claim_postures["advisor_journey_backend_evidence_available"] == "BACKEND_BACKED_UI_PENDING"
    )
    assert claim_postures["advisor_use_document_proof_available"] == "BACKEND_BACKED_UI_PENDING"
    assert claim_postures["ai_policy_cockpit_proof_integrated"] == "IMPLEMENTATION_BACKED"
    assert claim_postures["commercial_rfp_security_material_available"] == "IMPLEMENTATION_BACKED"
    assert claim_postures["rfp_security_package_pending"] == "UNSUPPORTED"
    assert claim_postures["client_ready_publication_blocked"] == "UNSUPPORTED"
    material_ids = {material.material_id for material in bundle.commercial_material_pack.materials}
    assert material_ids == {
        "product_one_pager",
        "rfp_response_pack",
        "security_posture_pack",
        "architecture_outline",
        "demo_script",
        "proof_pack_interpretation_guide",
        "roi_story",
        "supported_feature_matrix",
        "client_demo_boundaries",
        "operator_demo_lead_checklist",
    }
    assert "client_ready_publication" in bundle.commercial_material_pack.blocked_claims
    assert (
        bundle.journey_integration_proof_summary.policy_evidence.client_ready_publication
        == "BLOCKED"
    )
    document_families = {
        document.document_family for document in bundle.document_proof_summary.documents
    }
    assert document_families == {"PROPOSAL_MEMO", "POLICY_SIGN_OFF"}
    assert all(
        document.archive_retention_posture == "OWNED_BY_LOTUS_ARCHIVE"
        for document in bundle.document_proof_summary.documents
    )
