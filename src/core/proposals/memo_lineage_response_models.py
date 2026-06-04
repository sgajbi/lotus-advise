from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.proposals.lifecycle_response_models import ProposalSummary
from src.core.proposals.memo_event_models import ProposalMemoAuditEvent
from src.core.proposals.memo_types import ProposalMemoLifecycleStatus


class ProposalMemoLineageItem(BaseModel):
    memo_id: str = Field(description="Persisted memo identifier.", examples=["memo_001"])
    proposal_version_no: int = Field(description="Owning proposal version number.", examples=[1])
    proposal_version_id: Optional[str] = Field(
        default=None,
        description="Owning proposal version identifier.",
        examples=["ppv_001"],
    )
    memo_status: str = Field(
        description="Memo evidence-pack readiness posture.", examples=["BLOCKED"]
    )
    lifecycle_status: ProposalMemoLifecycleStatus = Field(
        description="Durable memo lifecycle status.",
        examples=["DRAFT"],
    )
    memo_hash: str = Field(description="Canonical memo hash.", examples=["sha256:memo"])
    source_input_hash: str = Field(
        description="Canonical hash of source memo input evidence.",
        examples=["sha256:source"],
    )
    created_at: str = Field(
        description="UTC ISO8601 memo creation timestamp.",
        examples=["2026-05-23T12:00:00+00:00"],
    )
    event_count: int = Field(description="Number of memo audit events for this memo.", examples=[1])
    report_package_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Latest report/render/archive posture recorded for this memo.",
    )
    archive_refs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Support-safe archive references derived from memo report-package events.",
    )
    ai_commentary_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Latest review-gated AI commentary posture recorded for this memo.",
    )


class ProposalMemoLineageResponse(BaseModel):
    proposal: ProposalSummary = Field(description="Proposal summary used as memo lineage root.")
    memo_count: int = Field(description="Number of persisted memos returned.", examples=[1])
    latest_memo_id: Optional[str] = Field(
        default=None,
        description="Latest memo identifier by proposal version and creation order.",
        examples=["memo_001"],
    )
    lineage_complete: bool = Field(
        description="Whether every returned memo has replay metadata and source hashes.",
        examples=[True],
    )
    memos: List[ProposalMemoLineageItem] = Field(
        default_factory=list,
        description="Persisted memo lineage ordered by proposal version.",
    )
    lineage_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supportability posture for memo lineage and product-promotion boundaries.",
        examples=[{"gateway_supported": False, "workbench_supported": False}],
    )


class ProposalMemoReplayEvidenceResponse(BaseModel):
    subject: Dict[str, Any] = Field(
        description="Memo replay subject identifiers.",
        examples=[{"proposal_id": "pp_001", "proposal_version_no": 1, "memo_id": "memo_001"}],
    )
    hashes: Dict[str, Any] = Field(
        description="Canonical proposal and memo hashes used to prove replay source identity.",
        examples=[{"memo_hash": "sha256:memo", "proposal_artifact_hash": "sha256:artifact"}],
    )
    replay_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Persisted memo replay metadata from the memo record.",
        examples=[{"replay_policy": "EXACT_SOURCE_HASH_MATCH"}],
    )
    audit_events: List[ProposalMemoAuditEvent] = Field(
        default_factory=list,
        description="Append-only memo audit events included in replay evidence.",
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Memo source evidence, projection, review, and report-package posture.",
        examples=[{"memo_status": "BLOCKED", "client_ready_publication": "BLOCKED"}],
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Human-readable replay explanation and unsupported product-surface boundaries.",
        examples=[{"source": "PERSISTED_MEMO_RECORD", "mutation_performed": False}],
    )


__all__ = [
    "ProposalMemoLineageItem",
    "ProposalMemoLineageResponse",
    "ProposalMemoReplayEvidenceResponse",
]
