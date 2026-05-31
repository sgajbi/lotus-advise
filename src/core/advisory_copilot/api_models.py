from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.models import (
    CopilotActionFamily,
    CopilotAudience,
    CopilotEvidencePacket,
    CopilotEvidenceSectionInput,
)
from src.core.advisory_copilot.records import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunRecord,
)
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.common.actors import normalize_required_actor_id


class AdvisoryCopilotEvidencePacketCreateRequest(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier supplied by the caller.",
        examples=["copilot_packet_pb_sg_001"],
    )
    action_family: CopilotActionFamily = Field(
        description="Governed copilot action family the packet supports.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the packet is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
    )
    audience: CopilotAudience = Field(
        description="Audience projection used for source-section filtering.",
        examples=["ADVISOR"],
    )
    source_sections: tuple[CopilotEvidenceSectionInput, ...] = Field(
        description="Bounded source-backed evidence sections to project into the packet.",
    )
    created_by: str = Field(
        description="Actor creating or rebuilding the packet.",
        examples=["advisor_123"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Business reason for packet creation; raw prompt fields are rejected.",
        examples=[{"business_reason": "Prepare advisor review."}],
    )

    @field_validator("created_by")
    @classmethod
    def _normalize_created_by(cls, value: str) -> str:
        return normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")


class AdvisoryCopilotProposalVersionEvidenceRequest(BaseModel):
    proposal_id: str = Field(
        description="Proposal identifier whose source-owned evidence should be projected.",
        examples=["proposal_sg_structured_note_001"],
    )
    proposal_version_no: int = Field(
        ge=1,
        description="Immutable proposal version number to use as the evidence source.",
        examples=[1],
    )
    evidence_packet_id: str | None = Field(
        default=None,
        description=(
            "Optional stable evidence-packet identifier. When omitted, Advise derives a "
            "deterministic identifier from action family, proposal, and version."
        ),
        examples=["copilot_packet_pb_sg_001"],
    )
    action_family: CopilotActionFamily = Field(
        description="Governed copilot action family the source projection supports.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    audience: CopilotAudience = Field(
        description="Audience projection used for role-aware evidence filtering.",
        examples=["ADVISOR"],
    )
    created_by: str = Field(
        description="Actor creating or rebuilding the source-owned packet projection.",
        examples=["advisor_123"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Business reason for packet creation; raw prompt fields are rejected.",
        examples=[{"business_reason": "Prepare advisor copilot review."}],
    )

    @field_validator("created_by")
    @classmethod
    def _normalize_created_by(cls, value: str) -> str:
        return normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")


class AdvisoryCopilotEvidencePacketResponse(BaseModel):
    evidence_packet: CopilotEvidencePacket = Field(
        description="Bounded, redacted copilot evidence packet."
    )
    record: AdvisoryCopilotEvidencePacketRecord = Field(
        description="Durable evidence-packet record and audit context."
    )


class AdvisoryCopilotActionRequest(BaseModel):
    evidence_packet_id: str = Field(
        description="Persisted evidence packet to use for copilot action execution.",
        examples=["copilot_packet_pb_sg_001"],
    )
    audience: CopilotAudience = Field(
        description="Audience projection requested for the action.",
        examples=["ADVISOR"],
    )
    requested_outputs: tuple[str, ...] = Field(
        description="Named business output sections requested from the governed action.",
        examples=[["advisor_review_summary"]],
    )
    requested_by: str = Field(
        description="Actor requesting the copilot action.",
        examples=["advisor_123"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Business reason for the action; raw prompt fields are rejected.",
        examples=[{"business_reason": "Prepare advisor review."}],
    )
    requested_intents: tuple[str, ...] = Field(
        default=(),
        description="Bounded requested intents used by guardrails before execution.",
        examples=[["explain_policy_posture"]],
    )
    user_instruction: str = Field(
        default="",
        description="Optional user instruction used only for guardrail evaluation and hashing.",
        examples=["Summarize advisor-use evidence."],
    )

    @field_validator("requested_by")
    @classmethod
    def _normalize_requested_by(cls, value: str) -> str:
        return normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")


class AdvisoryCopilotRunResponse(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Persisted advisory copilot run.")
    reviews: tuple[AdvisoryCopilotReviewRecord, ...] = Field(
        default=(),
        description="Ordered review audit events for the run.",
    )
    replayed: bool = Field(
        default=False,
        description="Whether the action request replayed an existing idempotent run.",
    )


class AdvisoryCopilotReviewRequest(BaseModel):
    action: CopilotReviewAction = Field(
        description="Review action to apply to the copilot run.",
        examples=["APPROVE_FOR_INTERNAL_USE"],
    )
    actor_id: str = Field(
        description="Actor recording the review event.",
        examples=["supervisor_123"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured review reason; raw prompt fields are rejected.",
        examples=[{"decision": "Reviewed against cited source evidence."}],
    )

    @field_validator("actor_id")
    @classmethod
    def _normalize_actor_id(cls, value: str) -> str:
        return normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")


class AdvisoryCopilotReviewResponse(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Run after review processing.")
    review: AdvisoryCopilotReviewRecord = Field(description="Persisted review event.")
    replayed: bool = Field(description="Whether this was an idempotent replay.")


class AdvisoryCopilotSupportabilityResponse(BaseModel):
    support_status: str = Field(
        description="Current support posture for the Advise copilot API surface.",
        examples=["ADVISE_COPILOT_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"],
    )
    client_ready_publication: str = Field(
        description="Client-ready publication posture for supported copilot output.",
        examples=["BLOCKED"],
    )
    supported_action_families: tuple[CopilotActionFamily, ...] = Field(
        description="Action families exposed by the Advise copilot API.",
    )
    boundaries: tuple[str, ...] = Field(
        description="Unsupported claims and system-of-record boundaries.",
    )


class AdvisoryCopilotRunPage(BaseModel):
    items: tuple[AdvisoryCopilotRunRecord, ...] = Field(
        description=(
            "Newest-first copilot runs for the requested proposal version scope, bounded by "
            "the requested page size."
        )
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor to request the next page, or null when the page is complete.",
    )
