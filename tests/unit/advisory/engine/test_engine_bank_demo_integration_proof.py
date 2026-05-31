from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    AdvisoryJourneyIntegrationProofSummary,
    AiModelRiskControlProof,
    CockpitEvidenceProof,
    PolicyEvidenceProof,
    build_journey_integration_proof_summary,
)
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import _live_runtime_payload


def _ai_control() -> AiModelRiskControlProof:
    return AiModelRiskControlProof(
        evidence_family="PROPOSAL_MEMO",
        proof_posture="IMPLEMENTATION_BACKED",
        ai_status="AI_ASSISTED_REVIEWED",
        authoritative_for_advice=False,
        human_review_required=True,
        raw_prompt_retained=False,
        raw_source_evidence_included=False,
        guardrail_status="CLIENT_READY_RELEASE_BLOCKED",
        lineage_complete=True,
    )


def _policy_evidence() -> PolicyEvidenceProof:
    return PolicyEvidenceProof(
        proof_posture="IMPLEMENTATION_BACKED",
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        evaluation_status="PENDING_REVIEW",
        material_rule_count=4,
        pending_rule_count=1,
        workflow_sign_off_status="PENDING_REVIEW",
        client_ready_publication="BLOCKED",
    )


def _integration_summary(
    *,
    required_workbench_panels: list[str] | None = None,
) -> AdvisoryJourneyIntegrationProofSummary:
    return AdvisoryJourneyIntegrationProofSummary(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        required_workbench_panels=required_workbench_panels
        or [
            "advisory.advisor_cockpit",
            "advisory.suitability_review",
            "proposal.memo_evidence_pack",
            "advisory.bank_demo_proof",
        ],
        ai_model_risk_controls=[_ai_control()],
        policy_evidence=_policy_evidence(),
        cockpit_evidence=CockpitEvidenceProof(
            proof_posture="IMPLEMENTATION_BACKED",
            client_ready_publication="BLOCKED",
        ),
        unsupported_claims=[
            "AI is not authoritative for advice, approval, policy sign-off, or publication.",
        ],
    )


def test_journey_integration_summary_preserves_canonical_ai_policy_boundaries() -> None:
    summary = build_journey_integration_proof_summary(_live_runtime_payload())

    assert summary.policy_evidence.pending_rule_count <= summary.policy_evidence.material_rule_count
    assert summary.cockpit_evidence.local_workflow_logic_allowed is False
    assert summary.required_workbench_panels == [
        "advisory.advisor_cockpit",
        "advisory.suitability_review",
        "proposal.memo_evidence_pack",
        "advisory.bank_demo_proof",
    ]


def test_ai_proof_rejects_sensitive_status_text() -> None:
    with pytest.raises(ValidationError, match="sensitive technical detail"):
        AiModelRiskControlProof(
            evidence_family="PROPOSAL_MEMO",
            proof_posture="IMPLEMENTATION_BACKED",
            ai_status="provider response available",
            authoritative_for_advice=False,
            human_review_required=True,
            raw_prompt_retained=False,
            raw_source_evidence_included=False,
            guardrail_status="CLIENT_READY_RELEASE_BLOCKED",
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        AiModelRiskControlProof(
            evidence_family="PROPOSAL_MEMO",
            proof_posture="IMPLEMENTATION_BACKED",
            ai_status="provider_response available",
            authoritative_for_advice=False,
            human_review_required=True,
            raw_prompt_retained=False,
            raw_source_evidence_included=False,
            guardrail_status="CLIENT_READY_RELEASE_BLOCKED",
        )


def test_policy_proof_rejects_impossible_rule_counts() -> None:
    with pytest.raises(ValidationError, match="pending rule count cannot exceed"):
        PolicyEvidenceProof(
            proof_posture="IMPLEMENTATION_BACKED",
            policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
            policy_version="2026.05",
            evaluation_status="PENDING_REVIEW",
            material_rule_count=1,
            pending_rule_count=2,
            workflow_sign_off_status="PENDING_REVIEW",
            client_ready_publication="BLOCKED",
        )


def test_integration_summary_rejects_duplicate_required_panels() -> None:
    with pytest.raises(ValidationError, match="required Workbench panels must be unique"):
        _integration_summary(
            required_workbench_panels=[
                "advisory.advisor_cockpit",
                "advisory.advisor_cockpit",
                "advisory.suitability_review",
                "proposal.memo_evidence_pack",
                "advisory.bank_demo_proof",
            ]
        )


def test_journey_integration_builder_rejects_malformed_source_payloads() -> None:
    missing_policy_field = deepcopy(_live_runtime_payload())
    del missing_policy_field["parity"]["proposal_policy"]["policy_pack_id"]

    with pytest.raises(ValueError, match="RFC0028_INTEGRATION_PROOF_FIELD_MISSING"):
        build_journey_integration_proof_summary(missing_policy_field)

    invalid_boolean = deepcopy(_live_runtime_payload())
    invalid_boolean["parity"]["proposal_memo"]["ai_review_required"] = "false"

    with pytest.raises(ValueError, match="RFC0028_INTEGRATION_PROOF_FIELD_INVALID"):
        build_journey_integration_proof_summary(invalid_boolean)

    invalid_integer = deepcopy(_live_runtime_payload())
    invalid_integer["parity"]["proposal_policy"]["material_rule_count"] = True

    with pytest.raises(ValueError, match="RFC0028_INTEGRATION_PROOF_FIELD_INVALID"):
        build_journey_integration_proof_summary(invalid_integer)
