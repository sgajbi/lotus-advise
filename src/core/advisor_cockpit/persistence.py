from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CockpitAcknowledgementRecord(BaseModel):
    acknowledgement_id: str = Field(
        description="Stable cockpit acknowledgement identifier.",
        examples=["ack_aci_policy_review_required_policy_eval_sg_001"],
    )
    action_item_id: str = Field(description="Acknowledged action item identifier.")
    action_item_version: int = Field(description="Action item version acknowledged by the actor.")
    acknowledged_by: str = Field(description="Actor that acknowledged the action item.")
    acknowledged_at: datetime = Field(description="UTC acknowledgement timestamp.")
    acknowledgement_note: str | None = Field(
        default=None, description="Support-safe acknowledgement note."
    )
    correlation_id: str | None = Field(default=None, description="Caller correlation id.")
    reason_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured acknowledgement reason and audit context.",
    )


class CockpitAcknowledgementIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(description="Acknowledgement idempotency key.")
    request_hash: str = Field(description="Canonical request hash.")
    acknowledgement_id: str = Field(description="Acknowledgement identifier mapped to the key.")
    action_item_id: str = Field(description="Acknowledged action item identifier.")
    created_at: datetime = Field(description="UTC idempotency mapping creation timestamp.")
