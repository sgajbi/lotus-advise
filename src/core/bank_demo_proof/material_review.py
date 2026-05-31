from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.bank_demo_proof.models import RFC28_CANONICAL_PORTFOLIO_ID
from src.core.bank_demo_proof.runtime_summary import value_at
from src.core.bank_demo_proof.validation import (
    RFC28_CAPTURE_CLAIM_REFS_MAX_ITEMS,
    RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    RFC28_CAPTURE_OBSERVED_VALUE_MAX_LENGTH,
    RFC28_CAPTURE_SOURCE_PATH_MAX_LENGTH,
    normalize_capture_text,
)


class MaterialFieldReview(BaseModel):
    review_id: str = Field(
        description="Stable material field review identifier.",
        max_length=RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
    )
    source_path: str = Field(
        description="Path in the sanitized live runtime suite payload.",
        max_length=RFC28_CAPTURE_SOURCE_PATH_MAX_LENGTH,
    )
    observed_value: Any = Field(description="Observed bounded value used for claim review.")
    expected_posture: str = Field(
        description="Expected posture for this material field.",
        max_length=RFC28_CAPTURE_OBSERVED_VALUE_MAX_LENGTH,
    )
    review_posture: Literal["PASS", "REVIEW_REQUIRED", "BLOCKED"] = Field(
        description="Review result for claim use."
    )
    claim_refs: list[str] = Field(
        default_factory=list,
        max_length=RFC28_CAPTURE_CLAIM_REFS_MAX_ITEMS,
        description="Supported-claim identifiers that depend on this field.",
    )

    @field_validator("review_id", "source_path", "expected_posture")
    @classmethod
    def _review_text_must_be_bounded(cls, value: str) -> str:
        return normalize_capture_text(value, field_name="material field review")

    @field_validator("observed_value")
    @classmethod
    def _observed_value_must_be_scalar_and_safe(cls, value: Any) -> Any:
        if isinstance(value, str):
            return normalize_capture_text(
                value,
                field_name="material field observed value",
                max_length=RFC28_CAPTURE_OBSERVED_VALUE_MAX_LENGTH,
            )
        if isinstance(value, bool) or isinstance(value, int) or value is None:
            return value
        raise ValueError("material field observed value must be a bounded scalar")

    @field_validator("claim_refs")
    @classmethod
    def _claim_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for item in value:
            normalized.append(normalize_capture_text(str(item), field_name="claim ref"))
        return normalized


_MATERIAL_FIELD_SPECS: tuple[tuple[str, str, Any, str], ...] = (
    (
        "canonical_portfolio",
        "parity.complete_issuer_portfolio",
        RFC28_CANONICAL_PORTFOLIO_ID,
        "backend_proof_capture_repeatable",
    ),
    (
        "lifecycle_state",
        "parity.lifecycle_current_state",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "async_lifecycle_state",
        "parity.async_lifecycle_current_state",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "workspace_rationale_lineage",
        "parity.workspace_rationale_supportability_status",
        "HISTORICAL",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "execution_handoff",
        "parity.execution_handoff_status",
        "REQUESTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "execution_terminal",
        "parity.execution_terminal_status",
        "EXECUTED",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "report_status",
        "parity.report_status",
        "READY",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "narrative_review",
        "parity.proposal_narrative.review_state",
        "APPROVED_FOR_ADVISOR_USE",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "narrative_client_ready",
        "parity.proposal_narrative.client_ready_status",
        "NOT_REQUESTED",
        "client_ready_publication_blocked",
    ),
    (
        "memo_review",
        "parity.proposal_memo.review_action",
        "APPROVE_FOR_ADVISOR_USE",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "memo_client_ready",
        "parity.proposal_memo.review_client_ready_publication",
        "BLOCKED",
        "client_ready_publication_blocked",
    ),
    (
        "policy_evaluation",
        "parity.proposal_policy.evaluation_status",
        "PENDING_REVIEW",
        "advisor_journey_backend_evidence_available",
    ),
    (
        "policy_client_ready",
        "parity.proposal_policy.workflow_client_ready_publication",
        "BLOCKED",
        "client_ready_publication_blocked",
    ),
    (
        "memo_document_render",
        "parity.proposal_memo.render_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_document_archive",
        "parity.proposal_memo.archive_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_archive_retention",
        "parity.proposal_memo.archive_retention_posture",
        "OWNED_BY_LOTUS_ARCHIVE",
        "advisor_use_document_proof_available",
    ),
    (
        "memo_archive_access_audit",
        "parity.proposal_memo.archive_access_audit_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_document_render",
        "parity.proposal_policy.render_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_document_archive",
        "parity.proposal_policy.archive_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_archive_retention",
        "parity.proposal_policy.archive_retention_posture",
        "OWNED_BY_LOTUS_ARCHIVE",
        "advisor_use_document_proof_available",
    ),
    (
        "policy_archive_access_audit",
        "parity.proposal_policy.archive_access_audit_ref_status",
        "RECORDED",
        "advisor_use_document_proof_available",
    ),
    (
        "narrative_guardrail_reproduction",
        "parity.proposal_narrative.guardrail_failure_status",
        "LOCAL_POLICY_REPRODUCED",
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "memo_ai_non_authoritative",
        "parity.proposal_memo.ai_authoritative_for_memo_status",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "memo_ai_review_required",
        "parity.proposal_memo.ai_review_required",
        True,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_non_authoritative",
        "parity.proposal_policy.ai_authoritative_for_policy_status",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_human_review_required",
        "parity.proposal_policy.ai_human_review_required",
        True,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_raw_source_excluded",
        "parity.proposal_policy.ai_raw_source_evidence_included",
        False,
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "policy_ai_forbidden_action_blocked",
        "parity.proposal_policy.forbidden_ai_action_block_status",
        "POLICY_AI_EVIDENCE_FORBIDDEN_ACTION",
        "ai_policy_cockpit_proof_integrated",
    ),
    (
        "degraded_risk",
        "degraded.risk_degraded_reason",
        "LOTUS_RISK_DEPENDENCY_UNAVAILABLE",
        "degraded_runtime_boundary_evidence_available",
    ),
    (
        "degraded_core",
        "degraded.core_degraded_reason",
        "LOTUS_CORE_DEPENDENCY_UNAVAILABLE",
        "degraded_runtime_boundary_evidence_available",
    ),
    (
        "insufficient_evidence",
        "degraded.insufficient_evidence_decision.decision_status",
        "INSUFFICIENT_EVIDENCE",
        "degraded_runtime_boundary_evidence_available",
    ),
)


def review_material_fields(live_runtime_payload: dict[str, Any]) -> list[MaterialFieldReview]:
    reviews: list[MaterialFieldReview] = []
    for review_id, source_path, expected_value, claim_ref in _MATERIAL_FIELD_SPECS:
        observed_value = value_at(live_runtime_payload, source_path)
        reviews.append(
            MaterialFieldReview(
                review_id=review_id,
                source_path=source_path,
                observed_value=observed_value,
                expected_posture=str(expected_value),
                review_posture="PASS" if observed_value == expected_value else "BLOCKED",
                claim_refs=[claim_ref],
            )
        )
    return reviews
