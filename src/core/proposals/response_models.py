from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_models import (
    ProposalNarrative,
    ProposalNarrativeClientAudience,
    ProposalNarrativeGenerationMode,
    ProposalNarrativeReviewRecord,
    ProposalNarrativeSectionKey,
)
from src.core.proposals.contract_types import (
    ProposalApprovalType,
    ProposalAsyncOperationStatus,
    ProposalAsyncOperationType,
    ProposalCreationStatus,
    ProposalWorkflowEventType,
    ProposalWorkflowState,
)
from src.core.proposals.delivery_response_models import (
    ProposalDeliveryExecutionSummary as ProposalDeliveryExecutionSummary,
)
from src.core.proposals.delivery_response_models import (
    ProposalDeliveryHistoryResponse as ProposalDeliveryHistoryResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalDeliveryReportingSummary as ProposalDeliveryReportingSummary,
)
from src.core.proposals.delivery_response_models import (
    ProposalDeliverySummaryResponse as ProposalDeliverySummaryResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalExecutionHandoffRequest as ProposalExecutionHandoffRequest,
)
from src.core.proposals.delivery_response_models import (
    ProposalExecutionHandoffResponse as ProposalExecutionHandoffResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalExecutionStatusResponse as ProposalExecutionStatusResponse,
)
from src.core.proposals.delivery_response_models import (
    ProposalExecutionUpdateRequest as ProposalExecutionUpdateRequest,
)
from src.core.proposals.delivery_response_models import (
    ProposalReportRequest as ProposalReportRequest,
)
from src.core.proposals.delivery_response_models import (
    ProposalReportResponse as ProposalReportResponse,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalApprovalRecord as ProposalApprovalRecord,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalCreateResponse as ProposalCreateResponse,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalDetailResponse as ProposalDetailResponse,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalListResponse as ProposalListResponse,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalSummary as ProposalSummary,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalVersionDetail as ProposalVersionDetail,
)
from src.core.proposals.lifecycle_response_models import (
    ProposalWorkflowEvent as ProposalWorkflowEvent,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoAiCommentaryRequest as ProposalMemoAiCommentaryRequest,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoAiCommentaryResponse as ProposalMemoAiCommentaryResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoAuditEvent as ProposalMemoAuditEvent,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoCommentarySection as ProposalMemoCommentarySection,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoCreateRequest as ProposalMemoCreateRequest,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoLifecycleStatus as ProposalMemoLifecycleStatus,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoLineageItem as ProposalMemoLineageItem,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoLineageResponse as ProposalMemoLineageResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoProjectionResponse as ProposalMemoProjectionResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReplayEvidenceResponse as ProposalMemoReplayEvidenceResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportOutputFormat as ProposalMemoReportOutputFormat,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportPackageEventRequest as ProposalMemoReportPackageEventRequest,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportPackageEventResponse as ProposalMemoReportPackageEventResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportPackageRequest as ProposalMemoReportPackageRequest,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportPackageResponse as ProposalMemoReportPackageResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReportPackageStatus as ProposalMemoReportPackageStatus,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoResponse as ProposalMemoResponse,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReviewAction as ProposalMemoReviewAction,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReviewRequest as ProposalMemoReviewRequest,
)
from src.core.proposals.memo_response_models import (
    ProposalMemoReviewResponse as ProposalMemoReviewResponse,
)


class ProposalNarrativeReadResponse(BaseModel):
    proposal: "ProposalSummary" = Field(
        description="Proposal summary for the immutable version that owns the narrative."
    )
    proposal_version_no: int = Field(
        description="Immutable proposal version number containing the persisted narrative.",
        examples=[1],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.", examples=["ppv_001"]
    )
    proposal_narrative: ProposalNarrative = Field(
        description="Exact persisted proposal narrative from the immutable proposal artifact."
    )
    narrative_review: Optional[ProposalNarrativeReviewRecord] = Field(
        default=None,
        description="Latest review event for this narrative, when one has been recorded.",
    )
    source_narrative_hash: str = Field(
        description="Canonical hash of the persisted narrative payload.",
        examples=["sha256:abc123"],
    )
    replay_evidence_path: str = Field(
        description="Canonical replay-evidence route for the owning proposal version.",
        examples=["/advisory/proposals/pp_001/versions/1/replay-evidence"],
    )
    read_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Read-only posture proving the route does not mutate the proposal version or "
            "promote client-ready publication."
        ),
        examples=[
            {
                "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
                "mutation_performed": False,
                "client_ready_publication": "GATED",
            }
        ],
    )


class ProposalNarrativeRegenerationRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting the regenerated advisor-review narrative candidate.",
        examples=["advisor_123"],
    )
    reason: str = Field(
        description="Human-readable reason for regeneration, captured for caller audit context.",
        examples=["Refresh advisor wording after review feedback."],
    )
    sections: Optional[List[ProposalNarrativeSectionKey]] = Field(
        default=None,
        description=(
            "Optional ordered section allowlist. When omitted, the current persisted narrative "
            "section set is regenerated."
        ),
        examples=[["EXECUTIVE_SUMMARY", "RISK_AND_CONCENTRATION"]],
    )
    generation_mode: ProposalNarrativeGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description=(
            "Regeneration mode. Deterministic template mode is the default; AI-assisted draft "
            "mode remains advisor-review only and still requires later review."
        ),
        examples=["DETERMINISTIC_TEMPLATE"],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional jurisdiction override for policy/disclosure selection.",
        examples=["SG"],
    )
    product_types: Optional[List[str]] = Field(
        default=None,
        description="Optional product-type override for disclosure policy selection.",
        examples=[["EQUITY", "FX"]],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Policy audience for the regenerated candidate. Client-ready publication remains "
            "gated even when this asks policy to evaluate client-ready blockers."
        ),
        examples=["ADVISOR_REVIEW"],
    )


class ProposalNarrativeRegenerationResponse(BaseModel):
    proposal: "ProposalSummary" = Field(
        description="Proposal summary for the immutable version used as regeneration source."
    )
    proposal_version_no: int = Field(
        description="Immutable proposal version number used as regeneration source.",
        examples=[1],
    )
    proposal_version_id: str = Field(
        description="Immutable proposal version identifier.", examples=["ppv_001"]
    )
    current_narrative_id: str = Field(
        description="Narrative id currently persisted on the immutable proposal version.",
        examples=["pn_current_001"],
    )
    regenerated_narrative: ProposalNarrative = Field(
        description=(
            "Non-persisted regenerated advisor-review narrative candidate built from the "
            "immutable proposal artifact."
        )
    )
    current_source_narrative_hash: str = Field(
        description="Canonical hash of the current persisted narrative payload.",
        examples=["sha256:abc123"],
    )
    regenerated_source_narrative_hash: str = Field(
        description="Canonical hash of the regenerated narrative candidate payload.",
        examples=["sha256:def456"],
    )
    source_artifact_hash: str = Field(
        description="Artifact hash of the immutable proposal version used for regeneration.",
        examples=["sha256:artifact"],
    )
    source_request_hash: str = Field(
        description="Request hash of the immutable proposal version used for regeneration.",
        examples=["sha256:request"],
    )
    latest_narrative_review: Optional[ProposalNarrativeReviewRecord] = Field(
        default=None,
        description="Latest review event for the current persisted narrative, when present.",
    )
    materially_changed: bool = Field(
        description="Whether the regenerated candidate hash differs from the persisted narrative.",
        examples=[False],
    )
    regeneration_posture: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Governed posture proving regeneration is non-persistent and still review-gated."
        ),
        examples=[
            {
                "source": "IMMUTABLE_PROPOSAL_VERSION_ARTIFACT",
                "persistence_status": "NOT_PERSISTED_REVIEW_REQUIRED",
                "mutation_performed": False,
                "client_ready_publication": "GATED",
                "review_required_before_report_package": True,
            }
        ],
    )


class ProposalVersionLineageItem(BaseModel):
    proposal_version_id: str = Field(
        description="Proposal version identifier.",
        examples=["ppv_001"],
    )
    version_no: int = Field(description="Proposal version number.", examples=[1])
    created_at: str = Field(
        description="UTC ISO8601 timestamp for version creation.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    status_at_creation: ProposalCreationStatus = Field(
        description="Simulation status captured at version creation.",
        examples=["READY"],
    )
    request_hash: str = Field(
        description="Canonical request hash for this version.",
        examples=["sha256:abc123"],
    )
    simulation_hash: str = Field(
        description="Canonical simulation-output hash for this version.",
        examples=["sha256:sim789"],
    )
    artifact_hash: str = Field(
        description="Canonical artifact hash for this version.",
        examples=["sha256:def456"],
    )


class ProposalLineageResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary used as lineage root context.",
        examples=[{"proposal_id": "pp_001", "current_version_no": 2}],
    )
    version_count: int = Field(
        description=(
            "Number of persisted immutable proposal versions returned in the lineage payload."
        ),
        examples=[2],
    )
    latest_version_no: Optional[int] = Field(
        default=None,
        description="Highest persisted proposal version number currently available in lineage.",
        examples=[2],
    )
    latest_version_created_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp of the latest persisted proposal version in lineage.",
        examples=["2026-02-19T12:10:00+00:00"],
    )
    lineage_complete: bool = Field(
        description=(
            "Whether every version number from 1 through current_version_no is present in "
            "advisory persistence."
        ),
        examples=[True],
    )
    missing_version_numbers: List[int] = Field(
        default_factory=list,
        description="Missing immutable version numbers detected while assembling proposal lineage.",
        examples=[[2]],
    )
    versions: List[ProposalVersionLineageItem] = Field(
        default_factory=list,
        description="Immutable proposal version lineage ordered by version number ascending.",
        examples=[[{"proposal_version_id": "ppv_001", "version_no": 1}]],
    )


class ProposalWorkflowTimelineResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured at workflow timeline retrieval time.",
        examples=[{"proposal_id": "pp_001", "current_state": "AWAITING_CLIENT_CONSENT"}],
    )
    current_state: ProposalWorkflowState = Field(
        description="Current workflow state at retrieval time.",
        examples=["AWAITING_CLIENT_CONSENT"],
    )
    event_count: int = Field(
        description="Number of append-only workflow events returned in the timeline payload.",
        examples=[3],
    )
    latest_event: Optional[ProposalWorkflowEvent] = Field(
        default=None,
        description="Latest workflow event in the append-only timeline.",
        examples=[{"event_type": "COMPLIANCE_APPROVED", "to_state": "AWAITING_CLIENT_CONSENT"}],
    )
    events: List[ProposalWorkflowEvent] = Field(
        default_factory=list,
        description="Append-only workflow events ordered by event occurrence.",
        examples=[[{"event_type": "CREATED", "to_state": "DRAFT"}]],
    )


class ProposalApprovalsResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured at approval-read retrieval time.",
        examples=[{"proposal_id": "pp_001", "current_state": "AWAITING_CLIENT_CONSENT"}],
    )
    approval_count: int = Field(
        description="Number of structured approval or consent records returned.",
        examples=[1],
    )
    latest_approval_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp of the latest returned approval or consent record.",
        examples=["2026-02-19T12:11:00+00:00"],
    )
    approvals: List[ProposalApprovalRecord] = Field(
        default_factory=list,
        description="Structured approval/consent records ordered by occurrence.",
        examples=[[{"approval_type": "COMPLIANCE", "approved": True}]],
    )


class ProposalIdempotencyLookupResponse(BaseModel):
    idempotency_key: str = Field(
        description="Idempotency key supplied on create request.",
        examples=["proposal-create-idem-001"],
    )
    request_hash: str = Field(
        description="Canonical request hash mapped to the idempotency key.",
        examples=["sha256:abc123"],
    )
    proposal_id: str = Field(
        description="Proposal identifier mapped by idempotency key.",
        examples=["pp_001"],
    )
    proposal_version_no: int = Field(
        description="Proposal version number mapped by idempotency key.", examples=[1]
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when idempotency mapping was persisted.",
        examples=["2026-02-19T12:00:00+00:00"],
    )


class ProposalAsyncAcceptedResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["pop_001"],
    )
    operation_type: ProposalAsyncOperationType = Field(
        description="Operation type queued for asynchronous execution.",
        examples=["CREATE_PROPOSAL"],
    )
    status: ProposalAsyncOperationStatus = Field(
        description="Initial operation status.",
        examples=["PENDING"],
    )
    correlation_id: str = Field(
        description="Correlation id used to trace asynchronous execution.",
        examples=["corr-proposal-async-001"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when operation was accepted.",
        examples=["2026-02-20T10:00:00+00:00"],
    )
    attempt_count: int = Field(
        description="Number of execution attempts already recorded for this operation.",
        examples=[0],
    )
    max_attempts: int = Field(
        description="Maximum number of runtime execution attempts before terminal failure.",
        examples=[3],
    )
    status_url: str = Field(
        description="Relative API path for operation status retrieval.",
        examples=["/advisory/proposals/operations/pop_001"],
    )


class ProposalAsyncError(BaseModel):
    code: str = Field(
        description="Stable operation error code.",
        examples=["PROPOSAL_NOT_FOUND"],
    )
    message: str = Field(
        description="Human-readable operation error message.",
        examples=["PROPOSAL_NOT_FOUND"],
    )


class ProposalAsyncOperationStatusResponse(BaseModel):
    operation_id: str = Field(
        description="Asynchronous operation identifier.",
        examples=["pop_001"],
    )
    operation_type: ProposalAsyncOperationType = Field(
        description="Operation type.",
        examples=["CREATE_PROPOSAL_VERSION"],
    )
    status: ProposalAsyncOperationStatus = Field(
        description="Current operation status.",
        examples=["SUCCEEDED"],
    )
    correlation_id: str = Field(
        description="Correlation id associated with this operation.",
        examples=["corr-proposal-async-001"],
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Idempotency key associated with operation when relevant.",
        examples=["proposal-create-idem-001"],
    )
    proposal_id: Optional[str] = Field(
        default=None,
        description="Proposal identifier scope for the operation when applicable.",
        examples=["pp_001"],
    )
    created_by: str = Field(
        description="Actor id that submitted the asynchronous operation.",
        examples=["advisor_123"],
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when operation was accepted.",
        examples=["2026-02-20T10:00:00+00:00"],
    )
    started_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution started.",
        examples=["2026-02-20T10:00:01+00:00"],
    )
    finished_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution finished.",
        examples=["2026-02-20T10:00:02+00:00"],
    )
    attempt_count: int = Field(
        description="Number of execution attempts already recorded for this operation.",
        examples=[1],
    )
    max_attempts: int = Field(
        description="Maximum number of runtime execution attempts before terminal failure.",
        examples=[3],
    )
    lease_expires_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when the current execution lease expires, when running.",
        examples=["2026-02-20T10:01:01+00:00"],
    )
    result: Optional[ProposalCreateResponse] = Field(
        default=None,
        description="Successful operation result payload when status is SUCCEEDED.",
        examples=[{"proposal": {"proposal_id": "pp_001", "current_state": "DRAFT"}}],
    )
    error: Optional[ProposalAsyncError] = Field(
        default=None,
        description="Failure details when status is FAILED.",
        examples=[{"code": "ProposalNotFoundError", "message": "PROPOSAL_NOT_FOUND"}],
    )


class ProposalStateTransitionRequest(BaseModel):
    event_type: ProposalWorkflowEventType = Field(
        description="Workflow event to apply on current proposal state.",
        examples=["SUBMITTED_FOR_COMPLIANCE_REVIEW"],
    )
    actor_id: str = Field(
        description="Actor id requesting the transition.",
        examples=["advisor_123"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Optional version this transition applies to.",
        examples=[2],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured transition reason payload for audit.",
        examples=[{"comment": "Compliance review required", "source": "advisor"}],
    )
    expected_state: Optional[ProposalWorkflowState] = Field(
        default=None,
        description="Optimistic concurrency check against current proposal state.",
        examples=["DRAFT"],
    )


class ProposalApprovalRequest(BaseModel):
    approval_type: ProposalApprovalType = Field(
        description="Approval type being recorded.",
        examples=["CLIENT_CONSENT"],
    )
    approved: bool = Field(description="Approval decision flag.", examples=[True])
    actor_id: str = Field(
        description="Actor id recording the approval.",
        examples=["client_abc"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Optional version number this approval applies to.",
        examples=[1],
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured approval metadata payload.",
        examples=[{"channel": "IN_PERSON", "captured_by": "advisor_1"}],
    )
    expected_state: Optional[ProposalWorkflowState] = Field(
        default=None,
        description="Optimistic concurrency check against current proposal state.",
        examples=["AWAITING_CLIENT_CONSENT"],
    )


class ProposalStateTransitionResponse(BaseModel):
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    current_state: ProposalWorkflowState = Field(
        description="Workflow state after transition.",
        examples=["COMPLIANCE_REVIEW"],
    )
    latest_workflow_event: ProposalWorkflowEvent = Field(
        description="Workflow event created by this operation.",
        examples=[
            {"event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW", "to_state": "COMPLIANCE_REVIEW"}
        ],
    )
    approval: Optional[ProposalApprovalRecord] = Field(
        default=None,
        description="Approval record created by this operation when applicable.",
        examples=[{"approval_type": "CLIENT_CONSENT", "approved": True}],
    )


class ProposalNarrativeReviewResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured after narrative review recording.",
        examples=[{"proposal_id": "pp_001", "current_version_no": 1}],
    )
    narrative_review: ProposalNarrativeReviewRecord = Field(
        description="Persisted narrative review event projection.",
        examples=[
            {
                "review_id": "pwe_narrative_review_001",
                "proposal_id": "pp_001",
                "proposal_version_no": 1,
                "narrative_id": "pn_001",
                "action": "APPROVE",
                "review_state": "APPROVED_FOR_ADVISOR_USE",
                "client_ready_status": "NOT_REQUESTED",
                "reviewed_by": "compliance_reviewer_001",
                "reviewed_at": "2026-05-22T08:30:00+00:00",
                "reason": "Narrative is evidence-grounded and suitable for advisor use.",
                "source_narrative_hash": "sha256:9c8a2f1d",
                "replacement_narrative_id": None,
                "replayed": False,
            }
        ],
    )
    latest_workflow_event: ProposalWorkflowEvent = Field(
        description="Append-only workflow event created or replayed for this narrative review.",
        examples=[{"event_type": "NARRATIVE_REVIEWED", "to_state": "DRAFT"}],
    )
