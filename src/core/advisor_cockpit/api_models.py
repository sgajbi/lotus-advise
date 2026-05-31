from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.core.advisor_cockpit.models import (
    AdvisorCockpitOperatingSnapshot,
    AdvisoryActionItem,
    CockpitAcknowledgementState,
    MeetingPreparationPacket,
)
from src.core.common.actors import normalize_optional_support_note, normalize_required_actor_id


class AdvisorCockpitAcknowledgeRequest(BaseModel):
    action_item_version: int = Field(
        ge=1,
        description="Action item version observed by the caller; stale versions are rejected.",
        examples=[1],
    )
    acknowledged_by: str = Field(
        description="Actor acknowledging the cockpit action item.",
        examples=["advisor_sg_001"],
    )
    acknowledgement_note: str | None = Field(
        default=None,
        description="Optional support-safe acknowledgement note.",
        examples=["Advisor has reviewed the pending compliance action."],
    )

    @field_validator("acknowledged_by")
    @classmethod
    def _normalize_acknowledged_by(cls, value: str) -> str:
        return normalize_required_actor_id(value, error_code="ACKNOWLEDGED_BY_REQUIRED")

    @field_validator("acknowledgement_note")
    @classmethod
    def _normalize_acknowledgement_note(cls, value: str | None) -> str | None:
        return normalize_optional_support_note(value)


class AdvisorCockpitAcknowledgeResponse(BaseModel):
    action_item: AdvisoryActionItem = Field(
        description="Action item with acknowledgement state attached."
    )
    acknowledgement: CockpitAcknowledgementState = Field(
        description="Persisted acknowledgement state."
    )
    replayed: bool = Field(
        description="Whether this response replayed an existing idempotent acknowledgement.",
        examples=[False],
    )
    audit: dict[str, Any] = Field(
        default_factory=dict,
        description="Support-safe acknowledgement audit context.",
        examples=[{"idempotency_key": "ack-idem-001", "correlation_id": "corr-cockpit-001"}],
    )


class AdvisorCockpitSupportabilityResponse(BaseModel):
    posture: str = Field(
        description="Current Advise-owned cockpit runtime posture.",
        examples=["ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"],
    )
    supportability: dict[str, Any] = Field(
        description="Support-safe source, API, persistence, and downstream readiness context."
    )
    unsupported_capabilities: list[str] = Field(
        description="Capabilities that remain explicitly unclaimable."
    )


class AdvisorCockpitPreparationPacketPage(BaseModel):
    items: list[MeetingPreparationPacket] = Field(
        default_factory=list,
        description="Source-backed meeting-preparation packets visible to the caller.",
    )
    next_cursor: str | None = Field(
        default=None,
        description="Opaque cursor for retrieving the next preparation-packet page.",
        examples=["prep_proposal_sg_001_v1"],
    )
    page_size: int = Field(description="Effective bounded page size.", examples=[25])
    total_count: int = Field(
        description="Total count within the bounded cockpit source scope.",
        examples=[1],
    )
    supportability: dict[str, Any] = Field(
        default_factory=dict,
        description="Support-safe source, API, and downstream readiness context.",
    )


class AdvisorCockpitSnapshotResponse(AdvisorCockpitOperatingSnapshot):
    """API response alias for Swagger grouping and future-compatible schema evolution."""
