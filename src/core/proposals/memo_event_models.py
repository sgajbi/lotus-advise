from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class ProposalMemoAuditEvent(BaseModel):
    event_id: str = Field(description="Memo audit event identifier.", examples=["pme_001"])
    event_type: str = Field(description="Memo event type.", examples=["MEMO_DRAFT_CREATED"])
    actor_id: str = Field(
        description="Actor that recorded the memo event.", examples=["advisor_123"]
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp when the memo event occurred.",
        examples=["2026-05-23T12:00:00+00:00"],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured memo event reason, hashes, idempotency, and source evidence.",
        examples=[{"memo_hash": "sha256:memo", "source_input_hash": "sha256:source"}],
    )


__all__ = ["ProposalMemoAuditEvent"]
