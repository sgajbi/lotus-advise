from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisory_copilot.packet_record_limits import (
    COPILOT_PACKET_RECORD_ACTOR_ID_MAX_LENGTH,
    COPILOT_PACKET_RECORD_HASH_MAX_LENGTH,
    COPILOT_PACKET_RECORD_IDENTIFIER_MAX_LENGTH,
    COPILOT_PACKET_RECORD_JSON_FIELD_MAX_ITEMS,
)
from src.core.advisory_copilot.record_text import (
    normalize_optional_record_text,
    normalize_required_record_text,
)
from src.core.advisory_copilot.type_models import CopilotActionFamily, CopilotAudience
from src.core.proposals.correlation import MAX_CORRELATION_ID_LENGTH


class AdvisoryCopilotEvidencePacketRecord(BaseModel):
    evidence_packet_id: str = Field(
        description="Evidence-packet identifier available for governed copilot actions.",
        examples=["copilot_packet_pb_sg_001"],
        min_length=1,
        max_length=COPILOT_PACKET_RECORD_IDENTIFIER_MAX_LENGTH,
    )
    evidence_packet_hash: str = Field(
        description="Canonical hash of the bounded evidence packet.",
        examples=["sha256:copilot-evidence-packet-001"],
        min_length=1,
        max_length=COPILOT_PACKET_RECORD_HASH_MAX_LENGTH,
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
        max_length=COPILOT_PACKET_RECORD_IDENTIFIER_MAX_LENGTH,
    )
    proposal_id: str | None = Field(
        default=None,
        description="Proposal identifier when the packet is proposal-scoped.",
        examples=["proposal_sg_structured_note_001"],
        min_length=1,
        max_length=COPILOT_PACKET_RECORD_IDENTIFIER_MAX_LENGTH,
    )
    created_by: str = Field(
        description="Actor that created or rebuilt the evidence packet.",
        examples=["advisor_123"],
        min_length=1,
        max_length=COPILOT_PACKET_RECORD_ACTOR_ID_MAX_LENGTH,
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
        max_length=COPILOT_PACKET_RECORD_JSON_FIELD_MAX_ITEMS,
    )
    reason_json: dict[str, Any] = Field(
        description="Business reason for creating or rebuilding the packet.",
        examples=[{"business_reason": "Prepare advisor review."}],
        max_length=COPILOT_PACKET_RECORD_JSON_FIELD_MAX_ITEMS,
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
        return cast(
            str,
            normalize_required_record_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED"),
        )

    @field_validator("proposal_id")
    @classmethod
    def _normalize_optional_packet_text(cls, value: str | None) -> str | None:
        return cast(
            str | None,
            normalize_optional_record_text(value, error_code="COPILOT_PACKET_RECORD_REQUIRED"),
        )
