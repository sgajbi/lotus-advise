from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import (
    ProposalApprovalType,
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
from src.core.proposals.narrative_response_models import (
    ProposalNarrativeReadResponse as ProposalNarrativeReadResponse,
)
from src.core.proposals.narrative_response_models import (
    ProposalNarrativeRegenerationRequest as ProposalNarrativeRegenerationRequest,
)
from src.core.proposals.narrative_response_models import (
    ProposalNarrativeRegenerationResponse as ProposalNarrativeRegenerationResponse,
)
from src.core.proposals.narrative_response_models import (
    ProposalNarrativeReviewResponse as ProposalNarrativeReviewResponse,
)
from src.core.proposals.operation_response_models import (
    ProposalAsyncAcceptedResponse as ProposalAsyncAcceptedResponse,
)
from src.core.proposals.operation_response_models import (
    ProposalAsyncError as ProposalAsyncError,
)
from src.core.proposals.operation_response_models import (
    ProposalAsyncOperationStatusResponse as ProposalAsyncOperationStatusResponse,
)
from src.core.proposals.operation_response_models import (
    ProposalIdempotencyLookupResponse as ProposalIdempotencyLookupResponse,
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
