from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, Field, field_validator

from src.core.advisor_cockpit.projection_bounds import (
    COCKPIT_IDENTIFIER_MAX_LENGTH,
    COCKPIT_SUMMARY_MAX_LENGTH,
    bounded_optional_reference,
    bounded_reference,
)
from src.core.common.actors import normalize_optional_support_note, normalize_required_actor_id

_ACKNOWLEDGEMENT_CONTEXT_MAX_KEYS = 64


class CockpitAcknowledgementRecord(BaseModel):
    acknowledgement_id: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Stable cockpit acknowledgement identifier.",
        examples=["ack_aci_policy_review_required_policy_eval_sg_001"],
    )
    action_item_id: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Acknowledged action item identifier.",
    )
    action_item_version: int = Field(
        ge=1,
        description="Action item version acknowledged by the actor.",
    )
    acknowledged_by: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Actor that acknowledged the action item.",
    )
    acknowledged_at: datetime = Field(description="UTC acknowledgement timestamp.")
    acknowledgement_note: str | None = Field(
        default=None,
        max_length=COCKPIT_SUMMARY_MAX_LENGTH,
        description="Support-safe acknowledgement note.",
    )
    correlation_id: str | None = Field(
        default=None,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Caller correlation id.",
    )
    reason_json: dict[str, Any] = Field(
        default_factory=dict,
        max_length=_ACKNOWLEDGEMENT_CONTEXT_MAX_KEYS,
        description="Structured acknowledgement reason and audit context.",
    )

    @field_validator("acknowledgement_id", "action_item_id", mode="before")
    @classmethod
    def _required_refs_must_be_bounded(cls, value: Any) -> str:
        return cast(str, bounded_reference(str(value)))

    @field_validator("acknowledged_by", mode="before")
    @classmethod
    def _acknowledged_by_must_be_actor_id(cls, value: Any) -> str:
        return cast(
            str,
            normalize_required_actor_id(str(value), error_code="ACKNOWLEDGED_BY_REQUIRED"),
        )

    @field_validator("acknowledgement_note")
    @classmethod
    def _acknowledgement_note_must_be_support_safe(cls, value: str | None) -> str | None:
        return cast(str | None, normalize_optional_support_note(value))

    @field_validator("correlation_id", mode="before")
    @classmethod
    def _correlation_id_must_be_bounded(cls, value: Any) -> str | None:
        if value is None:
            return None
        return cast(str | None, bounded_optional_reference(str(value)))


class CockpitAcknowledgementIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Acknowledgement idempotency key.",
    )
    request_hash: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Canonical request hash.",
    )
    acknowledgement_id: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Acknowledgement identifier mapped to the key.",
    )
    action_item_id: str = Field(
        min_length=1,
        max_length=COCKPIT_IDENTIFIER_MAX_LENGTH,
        description="Acknowledged action item identifier.",
    )
    created_at: datetime = Field(description="UTC idempotency mapping creation timestamp.")

    @field_validator(
        "idempotency_key",
        "request_hash",
        "acknowledgement_id",
        "action_item_id",
        mode="before",
    )
    @classmethod
    def _idempotency_refs_must_be_bounded(cls, value: Any) -> str:
        return cast(str, bounded_reference(str(value)))
