from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.proposals.delivery_response_models import ProposalReportResponse
from src.core.proposals.lifecycle_response_models import ProposalSummary
from src.core.proposals.memo_request_models import (
    ProposalMemoAiCommentaryRequest,  # noqa: F401
    ProposalMemoCreateRequest,  # noqa: F401
    ProposalMemoReportPackageEventRequest,  # noqa: F401
    ProposalMemoReportPackageRequest,  # noqa: F401
    ProposalMemoReviewRequest,  # noqa: F401
)
from src.core.proposals.memo_types import (
    ProposalMemoCommentarySection,  # noqa: F401
    ProposalMemoLifecycleStatus,
    ProposalMemoReportOutputFormat,  # noqa: F401
    ProposalMemoReportPackageStatus,  # noqa: F401
    ProposalMemoReviewAction,  # noqa: F401
)


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


class ProposalMemoResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary for the immutable version that owns the memo."
    )
    proposal_version_no: int = Field(
        description="Immutable proposal version number used as memo source.",
        examples=[1],
    )
    proposal_version_id: Optional[str] = Field(
        default=None,
        description="Immutable proposal version identifier used as memo source.",
        examples=["ppv_001"],
    )
    memo_id: str = Field(
        description="Deterministic persisted memo identifier.", examples=["memo_001"]
    )
    artifact_id: Optional[str] = Field(
        default=None,
        description="Proposal artifact identifier used as memo source.",
        examples=["pa_001"],
    )
    memo_version: str = Field(
        description="Memo evidence-pack schema version.",
        examples=["advisory-proposal-memo-evidence-pack.v1"],
    )
    memo_status: str = Field(
        description="Source-readiness posture of the memo evidence pack.",
        examples=["BLOCKED"],
    )
    lifecycle_status: ProposalMemoLifecycleStatus = Field(
        description="Durable memo lifecycle status.",
        examples=["DRAFT"],
    )
    created_by: str = Field(description="Actor that created the memo.", examples=["advisor_123"])
    created_at: str = Field(
        description="UTC ISO8601 timestamp when the memo was created.",
        examples=["2026-05-23T12:00:00+00:00"],
    )
    source_input_hash: str = Field(
        description="Canonical hash of source proposal evidence used by the memo builder.",
        examples=["sha256:source"],
    )
    memo_hash: str = Field(
        description="Canonical hash of the persisted memo evidence pack.",
        examples=["sha256:memo"],
    )
    memo: Dict[str, Any] = Field(
        description="Persisted `AdvisoryProposalMemoEvidencePack:v1` JSON.",
        examples=[{"memo_id": "memo_001", "status": "BLOCKED"}],
    )
    projection: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Projection and publication policy for advisor, compliance, operations, and "
            "client-draft audiences."
        ),
        examples=[{"advisor_publication": "AVAILABLE", "client_ready_publication": "BLOCKED"}],
    )
    review_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Latest memo review posture derived from append-only memo audit events.",
        examples=[{"latest_review_action": "APPROVE_FOR_ADVISOR_USE"}],
    )
    report_package_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Latest report-package posture derived from memo audit events.",
        examples=[{"latest_report_package_status": "RECORDED"}],
    )
    ai_commentary_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Latest review-gated AI commentary posture derived from memo audit events.",
        examples=[{"ai_status": "REVIEW_REQUIRED"}],
    )
    replay_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Replay metadata proving proposal source hashes and memo request hashes.",
        examples=[{"proposal_artifact_hash": "sha256:artifact"}],
    )
    audit_events: List[ProposalMemoAuditEvent] = Field(
        default_factory=list,
        description="Append-only memo audit events ordered by occurrence.",
    )
    event_count: int = Field(description="Number of memo audit events returned.", examples=[1])
    replay_evidence_path: str = Field(
        description="Canonical memo replay-evidence route.",
        examples=["/advisory/proposals/pp_001/versions/1/memo/replay-evidence"],
    )
    lineage_path: str = Field(
        description="Canonical proposal memo lineage route.",
        examples=["/advisory/proposals/pp_001/memos/lineage"],
    )
    read_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supportability posture proving the response is not client-ready publication.",
        examples=[
            {
                "source": "PERSISTED_MEMO_RECORD",
                "client_ready_publication": "BLOCKED",
                "gateway_supported": False,
            }
        ],
    )


class ProposalMemoProjectionResponse(BaseModel):
    proposal: ProposalSummary = Field(description="Proposal summary for the memo projection.")
    proposal_version_no: int = Field(
        description="Immutable proposal version number used as memo source.",
        examples=[1],
    )
    memo_id: str = Field(description="Persisted memo identifier.", examples=["memo_001"])
    memo_hash: str = Field(description="Canonical persisted memo hash.", examples=["sha256:memo"])
    audience: Optional[str] = Field(
        default=None,
        description="Optional audience filter supplied by the caller.",
        examples=["ADVISOR"],
    )
    projection: Dict[str, Any] = Field(
        default_factory=dict,
        description="Projection policy for memo audiences and publication states.",
        examples=[{"client_ready_publication": "BLOCKED"}],
    )
    sections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Projected memo sections visible to the requested audience, or all internal sections "
            "when no audience is supplied."
        ),
    )
    projection_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description="Projection supportability posture and blocked client-ready status.",
        examples=[{"client_ready_publication": "BLOCKED", "mutation_performed": False}],
    )


class ProposalMemoReviewResponse(BaseModel):
    memo: ProposalMemoResponse = Field(description="Memo response after review event recording.")
    review_event: ProposalMemoAuditEvent = Field(description="Created or replayed review event.")
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent review event.",
        examples=[False],
    )


class ProposalMemoReportPackageEventResponse(BaseModel):
    memo: ProposalMemoResponse = Field(
        description="Memo response after report-package event recording."
    )
    report_package_event: ProposalMemoAuditEvent = Field(
        description="Created or replayed report-package event."
    )
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent report-package event.",
        examples=[False],
    )


class ProposalMemoReportPackageResponse(BaseModel):
    memo: ProposalMemoResponse = Field(
        description="Memo response after report/render/archive package request recording."
    )
    report_package_event: ProposalMemoAuditEvent = Field(
        description="Created or replayed report-package materialization event."
    )
    report: ProposalReportResponse = Field(
        description="lotus-report job handle and materialization references."
    )
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent report-package event.",
        examples=[False],
    )


class ProposalMemoAiCommentaryResponse(BaseModel):
    memo: ProposalMemoResponse = Field(
        description="Memo response after AI commentary lineage recording."
    )
    ai_event: ProposalMemoAuditEvent = Field(
        description="Created or replayed memo AI reference event."
    )
    commentary: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Review-gated AI commentary payload or deterministic unavailable posture. This "
            "payload is non-authoritative and cannot change memo evidence or approval posture."
        ),
    )
    replayed: bool = Field(
        description="Whether the request replayed an existing idempotent AI commentary event.",
        examples=[False],
    )


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
