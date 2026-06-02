from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.api_limits import (
    COPILOT_ACTOR_ID_MAX_LENGTH,
    COPILOT_IDENTIFIER_MAX_LENGTH,
    COPILOT_REQUESTED_INTENT_LIMIT,
    COPILOT_REQUESTED_INTENT_MAX_LENGTH,
    COPILOT_REQUESTED_OUTPUT_LIMIT,
    COPILOT_REQUESTED_OUTPUT_MAX_LENGTH,
    COPILOT_USER_INSTRUCTION_MAX_LENGTH,
)
from src.core.advisory_copilot.api_validation import (
    normalize_bounded_copilot_string_tuple,
    normalize_copilot_actor_id,
    normalize_copilot_user_instruction,
    normalize_optional_copilot_identifier,
    normalize_required_copilot_identifier,
)
from src.core.advisory_copilot.packet_models import COPILOT_PACKET_SECTION_LIMIT
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.type_models import CopilotActionFamily, CopilotAudience


class AdvisoryCopilotEvidencePacketCreateRequest(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier supplied by the caller.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Governed copilot action family the packet supports.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
        examples=["PB_SG_GLOBAL_BAL_001"],
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the packet is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    audience: CopilotAudience = Field(
        description="Audience projection used for source-section filtering.",
        examples=["ADVISOR"],
    )
    source_sections: tuple[CopilotEvidenceSectionInput, ...] = Field(
        description="Bounded source-backed evidence sections to project into the packet.",
        max_length=COPILOT_PACKET_SECTION_LIMIT,
    )
    created_by: str = Field(
        description="Actor creating or rebuilding the packet.",
        examples=["advisor_123"],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Business reason for packet creation; unredacted AI-input fields are rejected.",
        examples=[{"business_reason": "Prepare advisor review."}],
    )

    @field_validator("created_by")
    @classmethod
    def _normalize_created_by(cls, value: str) -> str:
        return normalize_copilot_actor_id(value)

    @field_validator("evidence_packet_id", "portfolio_id")
    @classmethod
    def _normalize_required_identifier(cls, value: str) -> str:
        return normalize_required_copilot_identifier(
            value,
            error_code="COPILOT_IDENTIFIER_REQUIRED",
        )

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_identifier(cls, value: str | None) -> str | None:
        return normalize_optional_copilot_identifier(value)


class AdvisoryCopilotProposalVersionEvidenceRequest(BaseModel):
    proposal_id: str = Field(
        description="Proposal identifier whose source-owned evidence should be projected.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
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
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
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
        description="Business reason for packet creation; unredacted AI-input fields are rejected.",
        examples=[{"business_reason": "Prepare advisor copilot review."}],
    )

    @field_validator("created_by")
    @classmethod
    def _normalize_created_by(cls, value: str) -> str:
        return normalize_copilot_actor_id(value)

    @field_validator("proposal_id")
    @classmethod
    def _normalize_proposal_id(cls, value: str) -> str:
        return normalize_required_copilot_identifier(
            value,
            error_code="COPILOT_PROPOSAL_ID_REQUIRED",
        )

    @field_validator("evidence_packet_id")
    @classmethod
    def _normalize_evidence_packet_id(cls, value: str | None) -> str | None:
        return normalize_optional_copilot_identifier(value)


class AdvisoryCopilotActionRequest(BaseModel):
    evidence_packet_id: str = Field(
        description="Persisted evidence packet to use for copilot action execution.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    audience: CopilotAudience = Field(
        description="Audience projection requested for the action.",
        examples=["ADVISOR"],
    )
    requested_outputs: tuple[str, ...] = Field(
        description="Named business output sections requested from the governed action.",
        examples=[["advisor_review_summary"]],
        min_length=1,
        max_length=COPILOT_REQUESTED_OUTPUT_LIMIT,
    )
    requested_by: str = Field(
        description="Actor requesting the copilot action.",
        examples=["advisor_123"],
        max_length=COPILOT_ACTOR_ID_MAX_LENGTH,
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Business reason for the action; unredacted AI-input fields are rejected.",
        examples=[{"business_reason": "Prepare advisor review."}],
    )
    requested_intents: tuple[str, ...] = Field(
        default=(),
        description="Bounded requested intents used by guardrails before execution.",
        examples=[["explain_policy_posture"]],
        max_length=COPILOT_REQUESTED_INTENT_LIMIT,
    )
    user_instruction: str = Field(
        default="",
        description="Optional user instruction used only for guardrail evaluation and hashing.",
        examples=["Summarize advisor-use evidence."],
        max_length=COPILOT_USER_INSTRUCTION_MAX_LENGTH,
    )

    @field_validator("requested_outputs", mode="before")
    @classmethod
    def _normalize_requested_outputs(cls, value: Any) -> tuple[str, ...]:
        return normalize_bounded_copilot_string_tuple(
            value,
            error_code="COPILOT_REQUESTED_OUTPUT_REQUIRED",
            max_items=COPILOT_REQUESTED_OUTPUT_LIMIT,
            max_item_length=COPILOT_REQUESTED_OUTPUT_MAX_LENGTH,
            allow_empty=False,
        )

    @field_validator("evidence_packet_id")
    @classmethod
    def _normalize_evidence_packet_id(cls, value: str) -> str:
        return normalize_required_copilot_identifier(
            value,
            error_code="COPILOT_EVIDENCE_PACKET_ID_REQUIRED",
        )

    @field_validator("requested_by")
    @classmethod
    def _normalize_requested_by(cls, value: str) -> str:
        return normalize_copilot_actor_id(value)

    @field_validator("requested_intents", mode="before")
    @classmethod
    def _normalize_requested_intents(cls, value: Any) -> tuple[str, ...]:
        return normalize_bounded_copilot_string_tuple(
            value,
            error_code="COPILOT_REQUESTED_INTENT_INVALID",
            max_items=COPILOT_REQUESTED_INTENT_LIMIT,
            max_item_length=COPILOT_REQUESTED_INTENT_MAX_LENGTH,
            allow_empty=True,
        )

    @field_validator("user_instruction")
    @classmethod
    def _normalize_user_instruction(cls, value: str) -> str:
        return normalize_copilot_user_instruction(value)


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
        description="Structured review reason; unredacted AI-input fields are rejected.",
        examples=[{"decision": "Reviewed against cited source evidence."}],
    )

    @field_validator("actor_id")
    @classmethod
    def _normalize_actor_id(cls, value: str) -> str:
        return normalize_copilot_actor_id(value)


__all__ = [
    "AdvisoryCopilotActionRequest",
    "AdvisoryCopilotEvidencePacketCreateRequest",
    "AdvisoryCopilotProposalVersionEvidenceRequest",
    "AdvisoryCopilotReviewRequest",
]
