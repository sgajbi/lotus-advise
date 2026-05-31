from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotClientReadyPosture,
    CopilotRetentionClass,
    CopilotReviewPosture,
)
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH
from src.core.proposals.correlation import MAX_CORRELATION_ID_LENGTH

CopilotRecordSchemaVersion = Literal["advisory-copilot-run-record.v1"]
CopilotReviewRecordSchemaVersion = Literal["advisory-copilot-review-record.v1"]

_COPILOT_ACTOR_ID_MAX_LENGTH = 128
_COPILOT_APP_ID_MAX_LENGTH = 64
_COPILOT_HASH_MAX_LENGTH = 128
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_JSON_FIELD_MAX_ITEMS = 64
_COPILOT_OUTPUT_SECTION_LIMIT = 64
_COPILOT_REVIEW_GUIDANCE_LIMIT = 16
_COPILOT_REVIEW_GUIDANCE_MAX_LENGTH = 500
_COPILOT_GUARDRAIL_REASON_LIMIT = 16
_COPILOT_GUARDRAIL_REASON_MAX_LENGTH = 160
_COPILOT_VERSION_REF_MAX_LENGTH = 160


class AdvisoryCopilotRunRecord(BaseModel):
    schema_version: CopilotRecordSchemaVersion = Field(
        default="advisory-copilot-run-record.v1",
        description="Stable schema version for persisted advisory copilot run records.",
        examples=["advisory-copilot-run-record.v1"],
    )
    run_id: str = Field(
        description="Stable advisory copilot run identifier.",
        examples=["copilot_run_a1b2c3"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Governed advisory copilot action family executed for this run.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    audience: CopilotAudience = Field(
        description="Audience projection requested for this run.",
        examples=["ADVISOR"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for the source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the run is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_id: str = Field(
        description="Evidence-packet identifier used to produce the run.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Canonical hash of the bounded evidence packet used by the run.",
        examples=["sha256:copilot-evidence-packet-001"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    request_hash: str = Field(
        description="Canonical hash of the safe run request; unredacted AI input is never stored.",
        examples=["sha256:copilot-request"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    output_hash: str = Field(
        description="Canonical hash of persisted review-gated copilot output sections.",
        examples=["sha256:copilot-output"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    review_posture: CopilotReviewPosture = Field(
        description="Current human-review posture for the copilot run.",
        examples=["REVIEW_REQUIRED"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture; supported copilot output is blocked.",
        examples=["BLOCKED"],
    )
    retention_class: CopilotRetentionClass = Field(
        description="Retention class inherited from the evidence packet.",
        examples=["ADVISORY_REVIEW_RECORD"],
    )
    legal_hold: bool = Field(
        default=False,
        description="Whether normal retention expiry is suspended for this run.",
        examples=[False],
    )
    retention_expires_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when retention may expire unless legal hold applies.",
        examples=["2033-05-28T00:00:00+00:00"],
    )
    created_by: str = Field(
        description="Actor that requested the copilot run.",
        examples=["advisor_123"],
        min_length=1,
        max_length=_COPILOT_ACTOR_ID_MAX_LENGTH,
    )
    caller_app: str = Field(
        description="Calling application recorded for audit lineage.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=_COPILOT_APP_ID_MAX_LENGTH,
    )
    tenant_id: str = Field(
        description="Tenant identifier used for the governed workflow-pack execution.",
        examples=["tenant-sg-001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    correlation_id: str = Field(
        description="Correlation id propagated across Advise and lotus-ai boundaries.",
        examples=["corr_rfc0027_copilot_001"],
        min_length=1,
        max_length=MAX_CORRELATION_ID_LENGTH,
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional idempotency key used for safe action replay.",
        examples=["copilot-action-idem-001"],
        min_length=1,
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
    )
    created_at: datetime = Field(
        description="UTC timestamp when the run record was created.",
        examples=["2026-05-28T09:00:00+00:00"],
    )
    updated_at: datetime = Field(
        description="UTC timestamp when the run record was last updated.",
        examples=["2026-05-28T09:05:00+00:00"],
    )
    lotus_ai_workflow_run_id: str | None = Field(
        default=None,
        description="lotus-ai workflow-pack run identifier when execution reached lotus-ai.",
        examples=["packrun_copilot_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    lotus_ai_model_version: str | None = Field(
        default=None,
        description="Model or provider version reported by lotus-ai when available.",
        examples=["lotus-ai-governed-model.v1"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    workflow_pack_id: str = Field(
        description="Approved lotus-ai workflow-pack identifier used for the run.",
        examples=["advisory_copilot_proposal_explanation.pack"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    workflow_pack_version: str = Field(
        description="Approved lotus-ai workflow-pack version used for the run.",
        examples=["v1"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    prompt_template_version: str = Field(
        description="Approved prompt-template lineage reference; no unredacted AI input is stored.",
        examples=["advisory-copilot-prompt-template.v1"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    output_schema_version: str = Field(
        description="Structured output schema lineage reference for this run.",
        examples=["advisory-copilot-output-schema.v1"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    evaluation_pack_ref: str = Field(
        description="Model-risk evaluation pack reference for the copilot action family.",
        examples=["advisory-copilot-eval-pack.v1"],
        min_length=1,
        max_length=_COPILOT_VERSION_REF_MAX_LENGTH,
    )
    evidence_packet_json: dict[str, Any] = Field(
        description="Bounded evidence packet JSON persisted for audit replay.",
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )
    request_summary_json: dict[str, Any] = Field(
        description=(
            "Safe request summary with hashes and requested outputs; unredacted AI inputs omitted."
        ),
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )
    output_sections_json: list[dict[str, Any]] = Field(
        description="Review-gated business-facing output sections; unsafe raw output omitted.",
        max_length=_COPILOT_OUTPUT_SECTION_LIMIT,
    )
    review_guidance_json: list[str] = Field(
        description="Business-facing reviewer guidance for this run.",
        max_length=_COPILOT_REVIEW_GUIDANCE_LIMIT,
    )
    guardrail_results_json: list[str] = Field(
        description="Stable guardrail reason codes applied to this run.",
        max_length=_COPILOT_GUARDRAIL_REASON_LIMIT,
    )
    lineage_json: dict[str, Any] = Field(
        description="Adapter, workflow-pack, evidence, and model-risk lineage.",
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )

    @field_validator(
        "run_id",
        "portfolio_id",
        "evidence_packet_id",
        "evidence_packet_hash",
        "request_hash",
        "output_hash",
        "created_by",
        "caller_app",
        "tenant_id",
        "correlation_id",
        "workflow_pack_id",
        "workflow_pack_version",
        "prompt_template_version",
        "output_schema_version",
        "evaluation_pack_ref",
    )
    @classmethod
    def _normalize_required_run_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_RUN_RECORD_REQUIRED")

    @field_validator(
        "proposal_id",
        "idempotency_key",
        "lotus_ai_workflow_run_id",
        "lotus_ai_model_version",
    )
    @classmethod
    def _normalize_optional_run_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, error_code="COPILOT_RUN_RECORD_REQUIRED")

    @field_validator("review_guidance_json", mode="before")
    @classmethod
    def _normalize_review_guidance(cls, value: Any) -> list[str]:
        return _normalize_bounded_text_list(
            value,
            max_items=_COPILOT_REVIEW_GUIDANCE_LIMIT,
            max_item_length=_COPILOT_REVIEW_GUIDANCE_MAX_LENGTH,
            error_code="COPILOT_REVIEW_GUIDANCE_INVALID",
        )

    @field_validator("guardrail_results_json", mode="before")
    @classmethod
    def _normalize_guardrail_results(cls, value: Any) -> list[str]:
        return _normalize_bounded_text_list(
            value,
            max_items=_COPILOT_GUARDRAIL_REASON_LIMIT,
            max_item_length=_COPILOT_GUARDRAIL_REASON_MAX_LENGTH,
            error_code="COPILOT_GUARDRAIL_RESULT_INVALID",
        )


class AdvisoryCopilotEvidencePacketRecord(BaseModel):
    evidence_packet_id: str = Field(
        description="Evidence-packet identifier available for governed copilot actions.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Canonical hash of the bounded evidence packet.",
        examples=["sha256:copilot-evidence-packet-001"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Copilot action family supported by the packet.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    audience: CopilotAudience = Field(
        description="Audience projection used when the packet was created.",
        examples=["ADVISOR"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for the source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the packet is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    created_by: str = Field(
        description="Actor that created or rebuilt the evidence packet.",
        examples=["advisor_123"],
        min_length=1,
        max_length=_COPILOT_ACTOR_ID_MAX_LENGTH,
    )
    created_at: datetime = Field(
        description="UTC timestamp when the packet record was created.",
        examples=["2026-05-28T09:00:00+00:00"],
    )
    correlation_id: str = Field(
        description="Correlation id recorded for packet creation.",
        examples=["corr_rfc0027_packet_001"],
        min_length=1,
        max_length=MAX_CORRELATION_ID_LENGTH,
    )
    packet_json: dict[str, Any] = Field(
        description="Bounded, redacted copilot evidence packet JSON.",
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )
    reason_json: dict[str, Any] = Field(
        description="Business reason for creating or rebuilding the packet.",
        examples=[{"business_reason": "Prepare advisor review."}],
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )

    @field_validator(
        "evidence_packet_id",
        "evidence_packet_hash",
        "portfolio_id",
        "created_by",
        "correlation_id",
    )
    @classmethod
    def _normalize_required_packet_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED")

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_packet_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED")


class AdvisoryCopilotRunIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key for a copilot action request.",
        min_length=1,
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to the idempotency key.",
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    run_id: str = Field(
        description="Copilot run identifier mapped to the idempotency key.",
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    created_at: datetime = Field(description="UTC timestamp when the mapping was created.")

    @field_validator("idempotency_key", "request_hash", "run_id")
    @classmethod
    def _normalize_required_idempotency_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_IDEMPOTENCY_RECORD_REQUIRED")


class AdvisoryCopilotReviewRecord(BaseModel):
    schema_version: CopilotReviewRecordSchemaVersion = Field(
        default="advisory-copilot-review-record.v1",
        description="Stable schema version for persisted advisory copilot review records.",
        examples=["advisory-copilot-review-record.v1"],
    )
    review_id: str = Field(
        description="Stable advisory copilot review event identifier.",
        examples=["copilot_review_a1b2c3"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    run_id: str = Field(
        description="Copilot run identifier reviewed by this event.",
        examples=["copilot_run_a1b2c3"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    action: CopilotReviewAction = Field(
        description="Human review action applied to the run.",
        examples=["APPROVE_FOR_INTERNAL_USE"],
    )
    previous_posture: CopilotReviewPosture = Field(
        description="Run review posture before the event was applied.",
        examples=["REVIEW_REQUIRED"],
    )
    new_posture: CopilotReviewPosture = Field(
        description="Run review posture after the event was applied.",
        examples=["APPROVED_FOR_INTERNAL_USE"],
    )
    actor_id: str = Field(
        description="Actor that recorded the review event.",
        examples=["supervisor_123"],
        min_length=1,
        max_length=_COPILOT_ACTOR_ID_MAX_LENGTH,
    )
    occurred_at: datetime = Field(
        description="UTC timestamp when the review event was recorded.",
        examples=["2026-05-28T09:10:00+00:00"],
    )
    reason_json: dict[str, Any] = Field(
        description=(
            "Structured review reason; unredacted AI input and unsafe output are never stored."
        ),
        examples=[{"comment": "Reviewed against source evidence."}],
        max_length=_COPILOT_JSON_FIELD_MAX_ITEMS,
    )
    request_hash: str = Field(
        description="Canonical hash of the review request for idempotent replay.",
        examples=["sha256:copilot-review-request"],
        min_length=1,
        max_length=_COPILOT_HASH_MAX_LENGTH,
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional idempotency key for safe review replay.",
        examples=["copilot-review-idem-001"],
        min_length=1,
        max_length=MAX_IDEMPOTENCY_KEY_LENGTH,
    )
    correlation_id: str = Field(
        description="Correlation id propagated for audit and diagnostics.",
        examples=["corr_rfc0027_review_001"],
        min_length=1,
        max_length=MAX_CORRELATION_ID_LENGTH,
    )

    @field_validator("review_id", "run_id", "actor_id", "request_hash", "correlation_id")
    @classmethod
    def _normalize_required_review_text(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="COPILOT_REVIEW_RECORD_REQUIRED")

    @field_validator("idempotency_key")
    @classmethod
    def _normalize_optional_review_text(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value, error_code="COPILOT_REVIEW_RECORD_REQUIRED")


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def _normalize_optional_text(value: str | None, *, error_code: str) -> str | None:
    if value is None:
        return None
    return _normalize_required_text(value, error_code=error_code)


def _normalize_bounded_text_list(
    value: Any,
    *,
    max_items: int,
    max_item_length: int,
    error_code: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error_code)
    normalized: list[str] = []
    for item in value:
        if len(normalized) >= max_items:
            raise ValueError(error_code)
        if not isinstance(item, str):
            raise ValueError(error_code)
        text = _normalize_required_text(item, error_code=error_code)
        if len(text) > max_item_length:
            raise ValueError(error_code)
        normalized.append(text)
    return normalized
