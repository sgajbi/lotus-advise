from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.models import (
    AdvisorCockpitOperatingSnapshot,
    AdvisoryActionItem,
    CockpitAcknowledgementState,
)


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


class AdvisorCockpitSnapshotResponse(AdvisorCockpitOperatingSnapshot):
    """API response alias for Swagger grouping and future-compatible schema evolution."""
