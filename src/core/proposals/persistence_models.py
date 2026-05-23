from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import (
    ProposalApprovalType,
    ProposalAsyncOperationStatus,
    ProposalAsyncOperationType,
    ProposalCreationStatus,
    ProposalLifecycleOrigin,
    ProposalWorkflowEventType,
    ProposalWorkflowState,
)


class ProposalRecord(BaseModel):
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    portfolio_id: str = Field(description="Internal portfolio identifier.", examples=["pf_01"])
    mandate_id: Optional[str] = Field(
        default=None, description="Internal mandate identifier.", examples=["mandate_1"]
    )
    jurisdiction: Optional[str] = Field(
        default=None, description="Internal jurisdiction code.", examples=["SG"]
    )
    created_by: str = Field(description="Internal creator actor id.", examples=["advisor_1"])
    created_at: datetime = Field(
        description="Internal creation timestamp.", examples=["2026-02-19T12:00:00+00:00"]
    )
    last_event_at: datetime = Field(
        description="Internal latest-event timestamp.", examples=["2026-02-19T12:05:00+00:00"]
    )
    current_state: ProposalWorkflowState = Field(
        description="Internal workflow state.", examples=["DRAFT"]
    )
    current_version_no: int = Field(description="Internal current version number.", examples=[1])
    title: Optional[str] = Field(
        default=None,
        description="Internal proposal title.",
        examples=["2026 client portfolio transition plan"],
    )
    advisor_notes: Optional[str] = Field(
        default=None,
        description="Internal advisor notes.",
        examples=["Client approved initial draft."],
    )
    lifecycle_origin: ProposalLifecycleOrigin = Field(
        default="DIRECT_CREATE",
        description="Internal advisory lifecycle origin classification.",
        examples=["DIRECT_CREATE"],
    )
    source_workspace_id: Optional[str] = Field(
        default=None,
        description=(
            "Internal workspace identifier recorded when the proposal originated from handoff."
        ),
        examples=["aws_001"],
    )


class ProposalVersionRecord(BaseModel):
    proposal_version_id: str = Field(
        description="Internal version identifier.", examples=["ppv_001"]
    )
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    version_no: int = Field(description="Internal version number.", examples=[1])
    created_at: datetime = Field(
        description="Internal version creation timestamp.", examples=["2026-02-19T12:00:00+00:00"]
    )
    request_hash: str = Field(description="Internal request hash.", examples=["sha256:abc"])
    artifact_hash: str = Field(description="Internal artifact hash.", examples=["sha256:def"])
    simulation_hash: str = Field(description="Internal simulation hash.", examples=["sha256:sim"])
    status_at_creation: ProposalCreationStatus = Field(
        description="Internal simulation status.", examples=["READY"]
    )
    proposal_result_json: Dict[str, Any] = Field(
        description="Internal proposal-result JSON.", examples=[{"status": "READY"}]
    )
    artifact_json: Dict[str, Any] = Field(
        description="Internal artifact JSON.", examples=[{"artifact_id": "pa_001"}]
    )
    evidence_bundle_json: Dict[str, Any] = Field(
        description="Internal evidence-bundle JSON.",
        examples=[{"hashes": {"artifact_hash": "sha256:def"}}],
    )
    gate_decision_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal gate-decision snapshot JSON.",
        examples=[{"gate": "CLIENT_CONSENT_REQUIRED"}],
    )


class ProposalWorkflowEventRecord(BaseModel):
    event_id: str = Field(description="Internal event identifier.", examples=["pwe_001"])
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    event_type: ProposalWorkflowEventType = Field(
        description="Internal workflow event type.", examples=["CREATED"]
    )
    from_state: Optional[ProposalWorkflowState] = Field(
        default=None, description="Internal previous state.", examples=["DRAFT"]
    )
    to_state: ProposalWorkflowState = Field(
        description="Internal next state.", examples=["COMPLIANCE_REVIEW"]
    )
    actor_id: str = Field(description="Internal actor id.", examples=["advisor_1"])
    occurred_at: datetime = Field(
        description="Internal event timestamp.", examples=["2026-02-19T12:00:00+00:00"]
    )
    reason_json: Dict[str, Any] = Field(
        description="Internal structured reason JSON.", examples=[{"comment": "submitted"}]
    )
    related_version_no: Optional[int] = Field(
        default=None, description="Internal related version number.", examples=[1]
    )


class ProposalApprovalRecordData(BaseModel):
    approval_id: str = Field(description="Internal approval identifier.", examples=["pap_001"])
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    approval_type: ProposalApprovalType = Field(
        description="Internal approval type.", examples=["CLIENT_CONSENT"]
    )
    approved: bool = Field(description="Internal approval flag.", examples=[True])
    actor_id: str = Field(description="Internal approver actor id.", examples=["client_1"])
    occurred_at: datetime = Field(
        description="Internal approval timestamp.", examples=["2026-02-19T12:10:00+00:00"]
    )
    details_json: Dict[str, Any] = Field(
        description="Internal approval details JSON.", examples=[{"channel": "IN_PERSON"}]
    )
    related_version_no: Optional[int] = Field(
        default=None, description="Internal related version number.", examples=[1]
    )


class ProposalIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Internal idempotency key.", examples=["proposal-create-idem-001"]
    )
    request_hash: str = Field(
        description="Internal canonical request hash.", examples=["sha256:abc"]
    )
    proposal_id: str = Field(description="Internal proposal identifier.", examples=["pp_001"])
    proposal_version_no: int = Field(
        description="Internal referenced version number.", examples=[1]
    )
    created_at: datetime = Field(
        description="Internal idempotency creation timestamp.",
        examples=["2026-02-19T12:00:00+00:00"],
    )


class ProposalSimulationIdempotencyRecord(BaseModel):
    idempotency_key: str = Field(
        description="Internal simulation idempotency key.",
        examples=["proposal-simulate-idem-001"],
    )
    request_hash: str = Field(
        description="Internal canonical request hash for simulation payload.",
        examples=["sha256:abc"],
    )
    response_json: Dict[str, Any] = Field(
        description="Internal serialized proposal simulation response payload.",
        examples=[{"proposal_run_id": "pr_001", "status": "READY"}],
    )
    created_at: datetime = Field(
        description="Internal simulation idempotency creation timestamp.",
        examples=["2026-02-19T12:00:00+00:00"],
    )


class ProposalTransitionResult(BaseModel):
    proposal: ProposalRecord = Field(
        description="Internal proposal aggregate snapshot after transition.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTION_READY"}],
    )
    event: ProposalWorkflowEventRecord = Field(
        description="Internal workflow event persisted in transition.",
        examples=[{"event_id": "pwe_001", "event_type": "CLIENT_CONSENT_RECORDED"}],
    )
    approval: Optional[ProposalApprovalRecordData] = Field(
        default=None,
        description="Internal approval record persisted in transition when applicable.",
        examples=[{"approval_id": "pap_001", "approval_type": "CLIENT_CONSENT"}],
    )


class ProposalAsyncOperationRecord(BaseModel):
    operation_id: str = Field(
        description="Internal async operation identifier.", examples=["pop_001"]
    )
    operation_type: ProposalAsyncOperationType = Field(
        description="Internal async operation type.",
        examples=["CREATE_PROPOSAL"],
    )
    status: ProposalAsyncOperationStatus = Field(
        description="Internal async operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Internal correlation id.",
        examples=["corr-proposal-async-001"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Internal idempotency key for create operations.",
        examples=["proposal-create-idem-001"],
    )
    proposal_id: Optional[str] = Field(
        default=None,
        description="Internal proposal identifier scope.",
        examples=["pp_001"],
    )
    created_by: str = Field(description="Internal submitting actor id.", examples=["advisor_123"])
    created_at: datetime = Field(
        description="Internal operation acceptance timestamp.",
        examples=["2026-02-20T10:00:00+00:00"],
    )
    payload_json: Dict[str, Any] = Field(
        default_factory=dict,
        description="Internal normalized request payload used for restart-safe execution.",
        examples=[{"created_by": "advisor_123"}],
    )
    attempt_count: int = Field(
        default=0,
        ge=0,
        description="Internal execution attempt count.",
        examples=[0],
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        description="Internal maximum number of runtime execution attempts.",
        examples=[3],
    )
    started_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation start timestamp.",
        examples=["2026-02-20T10:00:01+00:00"],
    )
    lease_expires_at: Optional[datetime] = Field(
        default=None,
        description="Internal execution lease expiry timestamp while an attempt is running.",
        examples=["2026-02-20T10:01:01+00:00"],
    )
    finished_at: Optional[datetime] = Field(
        default=None,
        description="Internal operation completion timestamp.",
        examples=["2026-02-20T10:00:02+00:00"],
    )
    result_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal serialized successful result payload.",
        examples=[{"proposal": {"proposal_id": "pp_001"}}],
    )
    error_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Internal serialized failure payload.",
        examples=[{"code": "PROPOSAL_NOT_FOUND", "message": "PROPOSAL_NOT_FOUND"}],
    )


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
