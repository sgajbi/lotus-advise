from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.models import (
    COPILOT_PACKET_SECTION_LIMIT,
    CopilotEvidencePacket,
)
from src.core.advisory_copilot.pagination import COPILOT_RUN_MAX_PAGE_SIZE
from src.core.advisory_copilot.records import (
    AdvisoryCopilotEvidencePacketRecord,
    AdvisoryCopilotReviewRecord,
    AdvisoryCopilotRunRecord,
)
from src.core.advisory_copilot.review import CopilotReviewAction
from src.core.advisory_copilot.section_models import CopilotEvidenceSectionInput
from src.core.advisory_copilot.type_models import CopilotActionFamily, CopilotAudience
from src.core.common.actors import normalize_required_actor_id

_COPILOT_ACTOR_ID_MAX_LENGTH = 128
_COPILOT_CURSOR_MAX_LENGTH = 512
_COPILOT_IDENTIFIER_MAX_LENGTH = 160
_COPILOT_REQUESTED_OUTPUT_LIMIT = 8
_COPILOT_REQUESTED_OUTPUT_MAX_LENGTH = 96
_COPILOT_REQUESTED_INTENT_LIMIT = 12
_COPILOT_REQUESTED_INTENT_MAX_LENGTH = 96
_COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT = 12
_COPILOT_SUPPORTABILITY_BOUNDARY_MAX_LENGTH = 160
_COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH = 160
_COPILOT_USER_INSTRUCTION_MAX_LENGTH = 1000


class AdvisoryCopilotEvidencePacketCreateRequest(BaseModel):
    evidence_packet_id: str = Field(
        description="Stable evidence-packet identifier supplied by the caller.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    action_family: CopilotActionFamily = Field(
        description="Governed copilot action family the packet supports.",
        examples=["PROPOSAL_EXPLANATION"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for source-scoped advisory evidence.",
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
        return _normalize_copilot_actor_id(value)

    @field_validator("evidence_packet_id", "portfolio_id")
    @classmethod
    def _normalize_required_identifier(cls, value: str) -> str:
        return _normalize_required_identifier(value, error_code="COPILOT_IDENTIFIER_REQUIRED")

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_identifier(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value)


class AdvisoryCopilotProposalVersionEvidenceRequest(BaseModel):
    proposal_id: str = Field(
        description="Proposal identifier whose source-owned evidence should be projected.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
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
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
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
        return _normalize_copilot_actor_id(value)

    @field_validator("proposal_id")
    @classmethod
    def _normalize_proposal_id(cls, value: str) -> str:
        return _normalize_required_identifier(value, error_code="COPILOT_PROPOSAL_ID_REQUIRED")

    @field_validator("evidence_packet_id")
    @classmethod
    def _normalize_evidence_packet_id(cls, value: str | None) -> str | None:
        return _normalize_optional_identifier(value)


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
        min_length=1,
        max_length=_COPILOT_IDENTIFIER_MAX_LENGTH,
    )
    audience: CopilotAudience = Field(
        description="Audience projection requested for the action.",
        examples=["ADVISOR"],
    )
    requested_outputs: tuple[str, ...] = Field(
        description="Named business output sections requested from the governed action.",
        examples=[["advisor_review_summary"]],
        min_length=1,
        max_length=_COPILOT_REQUESTED_OUTPUT_LIMIT,
    )
    requested_by: str = Field(
        description="Actor requesting the copilot action.",
        examples=["advisor_123"],
        max_length=_COPILOT_ACTOR_ID_MAX_LENGTH,
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
        max_length=_COPILOT_REQUESTED_INTENT_LIMIT,
    )
    user_instruction: str = Field(
        default="",
        description="Optional user instruction used only for guardrail evaluation and hashing.",
        examples=["Summarize advisor-use evidence."],
        max_length=_COPILOT_USER_INSTRUCTION_MAX_LENGTH,
    )

    @field_validator("requested_outputs", mode="before")
    @classmethod
    def _normalize_requested_outputs(cls, value: Any) -> tuple[str, ...]:
        return _normalize_bounded_string_tuple(
            value,
            error_code="COPILOT_REQUESTED_OUTPUT_REQUIRED",
            max_items=_COPILOT_REQUESTED_OUTPUT_LIMIT,
            max_item_length=_COPILOT_REQUESTED_OUTPUT_MAX_LENGTH,
            allow_empty=False,
        )

    @field_validator("evidence_packet_id")
    @classmethod
    def _normalize_evidence_packet_id(cls, value: str) -> str:
        return _normalize_required_identifier(
            value,
            error_code="COPILOT_EVIDENCE_PACKET_ID_REQUIRED",
        )

    @field_validator("requested_by")
    @classmethod
    def _normalize_requested_by(cls, value: str) -> str:
        return _normalize_copilot_actor_id(value)

    @field_validator("requested_intents", mode="before")
    @classmethod
    def _normalize_requested_intents(cls, value: Any) -> tuple[str, ...]:
        return _normalize_bounded_string_tuple(
            value,
            error_code="COPILOT_REQUESTED_INTENT_INVALID",
            max_items=_COPILOT_REQUESTED_INTENT_LIMIT,
            max_item_length=_COPILOT_REQUESTED_INTENT_MAX_LENGTH,
            allow_empty=True,
        )

    @field_validator("user_instruction")
    @classmethod
    def _normalize_user_instruction(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) > _COPILOT_USER_INSTRUCTION_MAX_LENGTH:
            raise ValueError("COPILOT_USER_INSTRUCTION_TOO_LONG")
        return normalized


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
        description="Structured review reason; unredacted AI-input fields are rejected.",
        examples=[{"decision": "Reviewed against cited source evidence."}],
    )

    @field_validator("actor_id")
    @classmethod
    def _normalize_actor_id(cls, value: str) -> str:
        return _normalize_copilot_actor_id(value)


def _normalize_copilot_actor_id(value: str) -> str:
    normalized = normalize_required_actor_id(value, error_code="COPILOT_ACTOR_REQUIRED")
    if len(normalized) > _COPILOT_ACTOR_ID_MAX_LENGTH:
        raise ValueError("COPILOT_ACTOR_TOO_LONG")
    return cast(str, normalized)


def _normalize_required_identifier(value: str, *, error_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_code)
    if len(normalized) > _COPILOT_IDENTIFIER_MAX_LENGTH:
        raise ValueError("COPILOT_IDENTIFIER_TOO_LONG")
    return normalized


def _normalize_optional_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_required_identifier(value, error_code="COPILOT_IDENTIFIER_REQUIRED")


class AdvisoryCopilotReviewResponse(BaseModel):
    run: AdvisoryCopilotRunRecord = Field(description="Run after review processing.")
    review: AdvisoryCopilotReviewRecord = Field(description="Persisted review event.")
    replayed: bool = Field(description="Whether this was an idempotent replay.")


class AdvisoryCopilotSupportabilityResponse(BaseModel):
    support_status: str = Field(
        description="Current support posture for the Advise copilot API surface.",
        examples=["ADVISE_COPILOT_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"],
        min_length=1,
        max_length=_COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH,
    )
    client_ready_publication: str = Field(
        description="Client-ready publication posture for supported copilot output.",
        examples=["BLOCKED"],
        min_length=1,
        max_length=_COPILOT_SUPPORTABILITY_STATUS_MAX_LENGTH,
    )
    supported_action_families: tuple[CopilotActionFamily, ...] = Field(
        description="Action families exposed by the Advise copilot API.",
        max_length=_COPILOT_REQUESTED_INTENT_LIMIT,
    )
    boundaries: tuple[str, ...] = Field(
        description="Unsupported claims and system-of-record boundaries.",
        max_length=_COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
    )

    @field_validator("boundaries", mode="before")
    @classmethod
    def _normalize_boundaries(cls, value: Any) -> tuple[str, ...]:
        return _normalize_bounded_string_tuple(
            value,
            error_code="COPILOT_SUPPORTABILITY_BOUNDARY_INVALID",
            max_items=_COPILOT_SUPPORTABILITY_BOUNDARY_LIMIT,
            max_item_length=_COPILOT_SUPPORTABILITY_BOUNDARY_MAX_LENGTH,
            allow_empty=True,
        )


class AdvisoryCopilotRunPage(BaseModel):
    items: tuple[AdvisoryCopilotRunRecord, ...] = Field(
        description=(
            "Newest-first copilot runs for the requested proposal version scope, bounded by "
            "the requested page size."
        ),
        max_length=COPILOT_RUN_MAX_PAGE_SIZE,
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor to request the next page, or null when the page is complete.",
        max_length=_COPILOT_CURSOR_MAX_LENGTH,
    )


def _normalize_bounded_string_tuple(
    value: Any,
    *,
    error_code: str,
    max_items: int,
    max_item_length: int,
    allow_empty: bool,
) -> tuple[str, ...]:
    if value is None:
        if allow_empty:
            return ()
        raise ValueError(error_code)
    if not isinstance(value, (list, tuple)):
        raise ValueError(error_code)

    normalized: list[str] = []
    for item in value:
        if len(normalized) >= max_items:
            raise ValueError(error_code)
        if not isinstance(item, str):
            raise ValueError(error_code)
        candidate = item.strip()
        if not candidate:
            raise ValueError(error_code)
        if len(candidate) > max_item_length:
            raise ValueError(error_code)
        if candidate not in normalized:
            normalized.append(candidate)

    if not normalized and not allow_empty:
        raise ValueError(error_code)
    return tuple(normalized)
