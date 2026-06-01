from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.record_text import (
    normalize_optional_record_text,
    normalize_required_record_text,
)
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.run_records import (
    AdvisoryCopilotRunRecord as AdvisoryCopilotRunRecord,
)
from src.core.advisory_copilot.run_records import (
    CopilotRecordSchemaVersion as CopilotRecordSchemaVersion,
)
from src.core.advisory_copilot.type_models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotReviewPosture,
)
from src.core.common.idempotency import MAX_IDEMPOTENCY_KEY_LENGTH
from src.core.proposals.correlation import MAX_CORRELATION_ID_LENGTH

CopilotReviewRecordSchemaVersion = Literal["advisory-copilot-review-record.v1"]

_COPILOT_ACTOR_ID_MAX_LENGTH = 128
_COPILOT_HASH_MAX_LENGTH = 128
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_JSON_FIELD_MAX_ITEMS = 64


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
        return normalize_required_record_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED")

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_packet_text(cls, value: str | None) -> str | None:
        return normalize_optional_record_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED")


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
        return normalize_required_record_text(
            value, error_code="COPILOT_IDEMPOTENCY_RECORD_REQUIRED"
        )


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
        return normalize_required_record_text(value, error_code="COPILOT_REVIEW_RECORD_REQUIRED")

    @field_validator("idempotency_key")
    @classmethod
    def _normalize_optional_review_text(cls, value: str | None) -> str | None:
        return normalize_optional_record_text(value, error_code="COPILOT_REVIEW_RECORD_REQUIRED")
