from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.record_text import (
    normalize_bounded_record_text_list,
    normalize_optional_record_text,
    normalize_required_record_text,
)
from src.core.advisory_copilot.run_record_limits import (
    COPILOT_RUN_ACTOR_ID_MAX_LENGTH,
    COPILOT_RUN_APP_ID_MAX_LENGTH,
    COPILOT_RUN_GUARDRAIL_REASON_LIMIT,
    COPILOT_RUN_GUARDRAIL_REASON_MAX_LENGTH,
    COPILOT_RUN_HASH_MAX_LENGTH,
    COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
    COPILOT_RUN_JSON_FIELD_MAX_ITEMS,
    COPILOT_RUN_OUTPUT_SECTION_LIMIT,
    COPILOT_RUN_REVIEW_GUIDANCE_LIMIT,
    COPILOT_RUN_REVIEW_GUIDANCE_MAX_LENGTH,
    COPILOT_RUN_VERSION_REF_MAX_LENGTH,
)
from src.core.advisory_copilot.type_models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotClientReadyPosture,
    CopilotRetentionClass,
    CopilotReviewPosture,
)
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH
from src.core.proposals.correlation import MAX_CORRELATION_ID_LENGTH

CopilotRecordSchemaVersion = Literal["advisory-copilot-run-record.v1"]


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
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
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
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the run is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_id: str = Field(
        description="Evidence-packet identifier used to produce the run.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Canonical hash of the bounded evidence packet used by the run.",
        examples=["sha256:copilot-evidence-packet-001"],
        min_length=1,
        max_length=COPILOT_RUN_HASH_MAX_LENGTH,
    )
    request_hash: str = Field(
        description="Canonical hash of the safe run request; unredacted AI input is never stored.",
        examples=["sha256:copilot-request"],
        min_length=1,
        max_length=COPILOT_RUN_HASH_MAX_LENGTH,
    )
    output_hash: str = Field(
        description="Canonical hash of persisted review-gated copilot output sections.",
        examples=["sha256:copilot-output"],
        min_length=1,
        max_length=COPILOT_RUN_HASH_MAX_LENGTH,
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
        max_length=COPILOT_RUN_ACTOR_ID_MAX_LENGTH,
    )
    caller_app: str = Field(
        description="Calling application recorded for audit lineage.",
        examples=["lotus-advise"],
        min_length=1,
        max_length=COPILOT_RUN_APP_ID_MAX_LENGTH,
    )
    tenant_id: str = Field(
        description="Tenant identifier used for the governed workflow-pack execution.",
        examples=["tenant-sg-001"],
        min_length=1,
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
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
        max_length=COPILOT_RUN_IDENTIFIER_MAX_LENGTH,
    )
    lotus_ai_model_version: str | None = Field(
        default=None,
        description="Model or provider version reported by lotus-ai when available.",
        examples=["lotus-ai-governed-model.v1"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    workflow_pack_id: str = Field(
        description="Approved lotus-ai workflow-pack identifier used for the run.",
        examples=["advisory_copilot_proposal_explanation.pack"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    workflow_pack_version: str = Field(
        description="Approved lotus-ai workflow-pack version used for the run.",
        examples=["v1"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    prompt_template_version: str = Field(
        description="Approved prompt-template lineage reference; no unredacted AI input is stored.",
        examples=["advisory-copilot-prompt-template.v1"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    output_schema_version: str = Field(
        description="Structured output schema lineage reference for this run.",
        examples=["advisory-copilot-output-schema.v1"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    evaluation_pack_ref: str = Field(
        description="Model-risk evaluation pack reference for the copilot action family.",
        examples=["advisory-copilot-eval-pack.v1"],
        min_length=1,
        max_length=COPILOT_RUN_VERSION_REF_MAX_LENGTH,
    )
    evidence_packet_json: dict[str, Any] = Field(
        description="Bounded evidence packet JSON persisted for audit replay.",
        max_length=COPILOT_RUN_JSON_FIELD_MAX_ITEMS,
    )
    request_summary_json: dict[str, Any] = Field(
        description=(
            "Safe request summary with hashes and requested outputs; unredacted AI inputs omitted."
        ),
        max_length=COPILOT_RUN_JSON_FIELD_MAX_ITEMS,
    )
    output_sections_json: list[dict[str, Any]] = Field(
        description="Review-gated business-facing output sections; unsafe raw output omitted.",
        max_length=COPILOT_RUN_OUTPUT_SECTION_LIMIT,
    )
    review_guidance_json: list[str] = Field(
        description="Business-facing reviewer guidance for this run.",
        max_length=COPILOT_RUN_REVIEW_GUIDANCE_LIMIT,
    )
    guardrail_results_json: list[str] = Field(
        description="Stable guardrail reason codes applied to this run.",
        max_length=COPILOT_RUN_GUARDRAIL_REASON_LIMIT,
    )
    lineage_json: dict[str, Any] = Field(
        description="Adapter, workflow-pack, evidence, and model-risk lineage.",
        max_length=COPILOT_RUN_JSON_FIELD_MAX_ITEMS,
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
        return cast(
            str,
            normalize_required_record_text(value, error_code="COPILOT_RUN_RECORD_REQUIRED"),
        )

    @field_validator(
        "proposal_id",
        "idempotency_key",
        "lotus_ai_workflow_run_id",
        "lotus_ai_model_version",
    )
    @classmethod
    def _normalize_optional_run_text(cls, value: str | None) -> str | None:
        return cast(
            str | None,
            normalize_optional_record_text(value, error_code="COPILOT_RUN_RECORD_REQUIRED"),
        )

    @field_validator("review_guidance_json", mode="before")
    @classmethod
    def _normalize_review_guidance(cls, value: Any) -> list[str]:
        return cast(
            list[str],
            normalize_bounded_record_text_list(
                value,
                max_items=COPILOT_RUN_REVIEW_GUIDANCE_LIMIT,
                max_item_length=COPILOT_RUN_REVIEW_GUIDANCE_MAX_LENGTH,
                error_code="COPILOT_REVIEW_GUIDANCE_INVALID",
            ),
        )

    @field_validator("guardrail_results_json", mode="before")
    @classmethod
    def _normalize_guardrail_results(cls, value: Any) -> list[str]:
        return cast(
            list[str],
            normalize_bounded_record_text_list(
                value,
                max_items=COPILOT_RUN_GUARDRAIL_REASON_LIMIT,
                max_item_length=COPILOT_RUN_GUARDRAIL_REASON_MAX_LENGTH,
                error_code="COPILOT_GUARDRAIL_RESULT_INVALID",
            ),
        )
