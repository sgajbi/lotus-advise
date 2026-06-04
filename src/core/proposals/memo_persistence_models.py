from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

ProposalMemoLifecycleStatus = Literal["DRAFT", "FINALIZED"]
ProposalMemoEventType = Literal[
    "MEMO_DRAFT_CREATED",
    "MEMO_FINALIZED",
    "MEMO_REVIEW_RECORDED",
    "MEMO_REPORT_PACKAGE_RECORDED",
    "MEMO_ARCHIVE_RECORDED",
    "MEMO_AI_REFERENCE_RECORDED",
]


class ProposalMemoRecord(BaseModel):
    memo_id: str = Field(description="Deterministic memo identifier.", examples=["memo_abc"])
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    proposal_version_no: int = Field(description="Immutable proposal version number.", examples=[1])
    proposal_version_id: Optional[str] = Field(
        default=None,
        description="Immutable proposal version identifier when available.",
        examples=["ppv_001"],
    )
    artifact_id: Optional[str] = Field(
        default=None,
        description="Proposal artifact identifier used to build the memo.",
        examples=["pa_001"],
    )
    memo_version: str = Field(
        description="Memo evidence-pack schema version.",
        examples=["advisory-proposal-memo-evidence-pack.v1"],
    )
    memo_status: str = Field(description="Memo evidence-pack readiness posture.")
    lifecycle_status: ProposalMemoLifecycleStatus = Field(
        description="Durable memo lifecycle status."
    )
    created_by: str = Field(description="Actor that created the memo record.")
    created_at: datetime = Field(description="Memo creation timestamp.")
    source_input_hash: str = Field(description="Canonical hash of source proposal evidence.")
    memo_hash: str = Field(description="Canonical hash of persisted memo JSON.")
    memo_json: Dict[str, Any] = Field(description="Canonical memo evidence-pack JSON.")
    projection_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Persisted projection posture for advisor/client/report audiences.",
    )
    review_events_json: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Memo review events attached to this memo record.",
    )
    report_package_events_json: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Report-package event refs attached to this memo record.",
    )
    archive_refs_json: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="Archive refs attached to this memo record.",
    )
    ai_refs_json: list[Dict[str, Any]] = Field(
        default_factory=list,
        description="AI lineage refs attached to this memo record.",
    )
    replay_metadata_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Replay metadata proving source hashes and idempotency posture.",
    )


class ProposalMemoIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(description="Internal memo idempotency key.")
    request_hash: str = Field(description="Canonical request hash mapped to this memo key.")
    memo_id: str = Field(description="Memo identifier mapped to the idempotency key.")
    proposal_id: str = Field(description="Proposal identifier mapped to the idempotency key.")
    proposal_version_no: int = Field(description="Proposal version mapped to the idempotency key.")
    created_at: datetime = Field(description="Memo idempotency mapping creation timestamp.")


class ProposalMemoEventRecord(BaseModel):
    event_id: str = Field(description="Internal memo event identifier.")
    memo_id: str = Field(description="Memo identifier.")
    proposal_id: str = Field(description="Proposal identifier.")
    proposal_version_no: int = Field(description="Proposal version number.")
    event_type: ProposalMemoEventType = Field(description="Memo event type.")
    actor_id: str = Field(description="Actor that created the memo event.")
    occurred_at: datetime = Field(description="Memo event timestamp.")
    reason_json: Dict[str, Any] = Field(description="Structured memo event reason JSON.")


__all__ = [
    "ProposalMemoEventRecord",
    "ProposalMemoEventType",
    "ProposalMemoIdempotencyRecord",
    "ProposalMemoLifecycleStatus",
    "ProposalMemoRecord",
]
