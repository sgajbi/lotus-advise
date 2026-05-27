from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotClientReadyPosture,
    CopilotRetentionClass,
    CopilotReviewPosture,
)
from src.core.advisory_copilot.review import CopilotReviewAction

CopilotRecordSchemaVersion = Literal["advisory-copilot-run-record.v1"]
CopilotReviewRecordSchemaVersion = Literal["advisory-copilot-review-record.v1"]


class AdvisoryCopilotRunRecord(BaseModel):
    schema_version: CopilotRecordSchemaVersion = Field(
        default="advisory-copilot-run-record.v1",
        description="Stable schema version for persisted advisory copilot run records.",
        examples=["advisory-copilot-run-record.v1"],
    )
    run_id: str = Field(
        description="Stable advisory copilot run identifier.",
        examples=["copilot_run_a1b2c3"],
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
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the run is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
    )
    evidence_packet_id: str = Field(
        description="Evidence-packet identifier used to produce the run.",
        examples=["copilot_packet_pb_sg_001"],
    )
    evidence_packet_hash: str = Field(
        description="Canonical hash of the bounded evidence packet used by the run.",
        examples=["sha256:copilot-evidence-packet-001"],
    )
    request_hash: str = Field(
        description="Canonical hash of the safe run request; raw prompt text is never stored.",
        examples=["sha256:copilot-request"],
    )
    output_hash: str = Field(
        description="Canonical hash of persisted review-gated copilot output sections.",
        examples=["sha256:copilot-output"],
    )
    review_posture: CopilotReviewPosture = Field(
        description="Current human-review posture for the copilot run.",
        examples=["REVIEW_REQUIRED"],
    )
    client_ready_publication: CopilotClientReadyPosture = Field(
        default="BLOCKED",
        description="Client-ready publication posture; first-wave copilot output is blocked.",
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
    )
    caller_app: str = Field(
        description="Calling application recorded for audit lineage.",
        examples=["lotus-advise"],
    )
    tenant_id: str = Field(
        description="Tenant identifier used for the governed workflow-pack execution.",
        examples=["tenant-sg-001"],
    )
    correlation_id: str = Field(
        description="Correlation id propagated across Advise and lotus-ai boundaries.",
        examples=["corr_rfc0027_copilot_001"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional idempotency key used for safe action replay.",
        examples=["copilot-action-idem-001"],
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
    )
    lotus_ai_model_version: str | None = Field(
        default=None,
        description="Model or provider version reported by lotus-ai when available.",
        examples=["stub-advisory-copilot-v1"],
    )
    workflow_pack_id: str = Field(
        description="Approved lotus-ai workflow-pack identifier used for the run.",
        examples=["advisory_copilot_proposal_explanation.pack"],
    )
    workflow_pack_version: str = Field(
        description="Approved lotus-ai workflow-pack version used for the run.",
        examples=["v1"],
    )
    prompt_template_version: str = Field(
        description="Approved prompt-template lineage reference; no raw prompt is stored.",
        examples=["advisory-copilot-prompt-template.v1"],
    )
    output_schema_version: str = Field(
        description="Structured output schema lineage reference for this run.",
        examples=["advisory-copilot-output-schema.v1"],
    )
    evaluation_pack_ref: str = Field(
        description="Model-risk evaluation pack reference for the copilot action family.",
        examples=["advisory-copilot-eval-pack.v1"],
    )
    evidence_packet_json: dict[str, Any] = Field(
        description="Bounded evidence packet JSON persisted for audit replay.",
    )
    request_summary_json: dict[str, Any] = Field(
        description="Safe request summary with hashes and requested outputs; raw prompts omitted.",
    )
    output_sections_json: list[dict[str, Any]] = Field(
        description="Review-gated business-facing output sections; unsafe raw output omitted.",
    )
    review_guidance_json: list[str] = Field(
        description="Business-facing reviewer guidance for this run.",
    )
    guardrail_results_json: list[str] = Field(
        description="Stable guardrail reason codes applied to this run.",
    )
    lineage_json: dict[str, Any] = Field(
        description="Adapter, workflow-pack, evidence, and model-risk lineage.",
    )


class AdvisoryCopilotRunIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(description="Idempotency key for a copilot action request.")
    request_hash: str = Field(description="Canonical request hash mapped to the idempotency key.")
    run_id: str = Field(description="Copilot run identifier mapped to the idempotency key.")
    created_at: datetime = Field(description="UTC timestamp when the mapping was created.")


class AdvisoryCopilotReviewRecord(BaseModel):
    schema_version: CopilotReviewRecordSchemaVersion = Field(
        default="advisory-copilot-review-record.v1",
        description="Stable schema version for persisted advisory copilot review records.",
        examples=["advisory-copilot-review-record.v1"],
    )
    review_id: str = Field(
        description="Stable advisory copilot review event identifier.",
        examples=["copilot_review_a1b2c3"],
    )
    run_id: str = Field(
        description="Copilot run identifier reviewed by this event.",
        examples=["copilot_run_a1b2c3"],
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
    )
    occurred_at: datetime = Field(
        description="UTC timestamp when the review event was recorded.",
        examples=["2026-05-28T09:10:00+00:00"],
    )
    reason_json: dict[str, Any] = Field(
        description="Structured review reason; raw prompts or unsafe output are never stored.",
        examples=[{"comment": "Reviewed against source evidence."}],
    )
    request_hash: str = Field(
        description="Canonical hash of the review request for idempotent replay.",
        examples=["sha256:copilot-review-request"],
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional idempotency key for safe review replay.",
        examples=["copilot-review-idem-001"],
    )
    correlation_id: str = Field(
        description="Correlation id propagated for audit and diagnostics.",
        examples=["corr_rfc0027_review_001"],
    )
