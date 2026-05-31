from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisor_cockpit.models import (
    AdvisorCockpitOperatingSnapshot,
    AdvisoryActionItem,
    CockpitAcknowledgementState,
    MeetingPreparationPacket,
)
from src.core.advisor_cockpit.pagination import COCKPIT_ACTION_MAX_PAGE_SIZE
from src.core.advisor_cockpit.projection_bounds import COCKPIT_IDENTIFIER_MAX_LENGTH
from src.core.common.actors import normalize_optional_support_note, normalize_required_actor_id

_COCKPIT_API_LIST_MAX_ITEMS = 64
_COCKPIT_API_CONTEXT_MAX_KEYS = 64


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
        return cast(str, normalize_required_actor_id(value, error_code="ACKNOWLEDGED_BY_REQUIRED"))

    @field_validator("acknowledgement_note")
    @classmethod
    def _normalize_acknowledgement_note(cls, value: str | None) -> str | None:
        return cast(str | None, normalize_optional_support_note(value))


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
        max_length=_COCKPIT_API_CONTEXT_MAX_KEYS,
        description="Support-safe acknowledgement audit context.",
        examples=[{"idempotency_key": "ack-idem-001", "correlation_id": "corr-cockpit-001"}],
    )


class AdvisorCockpitSupportabilityResponse(BaseModel):
    posture: str = Field(
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Current Advise-owned cockpit runtime posture.",
        examples=["ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"],
    )
    supportability: dict[str, Any] = Field(
        max_length=_COCKPIT_API_CONTEXT_MAX_KEYS,
        description="Support-safe source, API, persistence, and downstream readiness context.",
    )
    unsupported_capabilities: list[str] = Field(
        max_length=_COCKPIT_API_LIST_MAX_ITEMS,
        description="Capabilities that remain explicitly unclaimable.",
    )


class AdvisorCockpitPreparationPacketPage(BaseModel):
    items: list[MeetingPreparationPacket] = Field(
        default_factory=list,
        max_length=_COCKPIT_API_LIST_MAX_ITEMS,
        description="Source-backed meeting-preparation packets visible to the caller.",
    )
    next_cursor: str | None = Field(
        default=None,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Opaque cursor for retrieving the next preparation-packet page.",
        examples=["prep_proposal_sg_001_v1"],
    )
    page_size: int = Field(
        ge=1,
        le=COCKPIT_ACTION_MAX_PAGE_SIZE,
        description="Effective bounded page size.",
        examples=[25],
    )
    total_count: int = Field(
        ge=0,
        description="Total count within the bounded cockpit source scope.",
        examples=[1],
    )
    supportability: dict[str, Any] = Field(
        default_factory=dict,
        max_length=_COCKPIT_API_CONTEXT_MAX_KEYS,
        description="Support-safe source, API, and downstream readiness context.",
    )


class AdvisorCockpitSnapshotResponse(AdvisorCockpitOperatingSnapshot):
    """API response alias for Swagger grouping and future-compatible schema evolution."""
