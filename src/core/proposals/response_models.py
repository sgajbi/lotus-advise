from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_models import ProposalNarrativeReviewRecord
from src.core.models import GateDecision, ProposalResult
from src.core.proposals.contract_types import (
    ProposalApprovalType,
    ProposalAsyncOperationStatus,
    ProposalAsyncOperationType,
    ProposalCreationStatus,
    ProposalExecutionHandoffStatus,
    ProposalExecutionUpdateStatus,
    ProposalLifecycleOrigin,
    ProposalReportType,
    ProposalWorkflowEventType,
    ProposalWorkflowState,
)
from src.core.proposals.execution_boundary import execution_ownership_boundary


class ProposalWorkflowEvent(BaseModel):
    event_id: str = Field(description="Workflow event identifier.", examples=["pwe_001"])
    proposal_id: str = Field(description="Proposal aggregate identifier.", examples=["pp_001"])
    event_type: ProposalWorkflowEventType = Field(
        description="Workflow event type.",
        examples=["SUBMITTED_FOR_RISK_REVIEW"],
    )
    from_state: Optional[ProposalWorkflowState] = Field(
        default=None,
        description="Previous workflow state before this event.",
        examples=["DRAFT"],
    )
    to_state: ProposalWorkflowState = Field(
        description="Workflow state after this event.",
        examples=["RISK_REVIEW"],
    )
    actor_id: str = Field(
        description="Actor id that triggered the event.", examples=["advisor_123"]
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the event.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured reason payload captured for audit.",
        examples=[{"comment": "Submitted after client call", "ticket_id": "wf_123"}],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Optional proposal version number referenced by this event.",
        examples=[1],
    )


class ProposalApprovalRecord(BaseModel):
    approval_id: str = Field(description="Approval record identifier.", examples=["pa_001"])
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    approval_type: ProposalApprovalType = Field(
        description="Approval domain type.",
        examples=["CLIENT_CONSENT"],
    )
    approved: bool = Field(description="Approval decision flag.", examples=[True])
    actor_id: str = Field(
        description="Actor id that recorded this approval.", examples=["client_001"]
    )
    occurred_at: str = Field(
        description="UTC ISO8601 timestamp for the approval.",
        examples=["2026-02-19T12:10:00+00:00"],
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured approval metadata, such as channel or document references.",
        examples=[{"channel": "IN_PERSON", "captured_by": "advisor_1"}],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Optional proposal version number referenced by this approval.",
        examples=[2],
    )


class ProposalVersionDetail(BaseModel):
    proposal_version_id: str = Field(
        description="Proposal version identifier.",
        examples=["ppv_001"],
    )
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    version_no: int = Field(description="Monotonic proposal version number.", examples=[1])
    created_at: str = Field(
        description="UTC ISO8601 timestamp for version creation.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    request_hash: str = Field(
        description="Canonical request hash for the version payload.",
        examples=["sha256:abc123"],
    )
    artifact_hash: str = Field(
        description="Canonical artifact hash for the immutable artifact JSON.",
        examples=["sha256:def456"],
    )
    simulation_hash: str = Field(
        description="Canonical hash of proposal simulation output.",
        examples=["sha256:sim789"],
    )
    status_at_creation: ProposalCreationStatus = Field(
        description="Proposal simulation status captured at version creation.",
        examples=["READY"],
    )
    proposal_result: ProposalResult = Field(
        description="Full proposal simulation output captured for this version.",
        examples=[{"proposal_run_id": "pr_abc12345", "status": "READY"}],
    )
    artifact: ProposalArtifact = Field(
        description="Full immutable proposal artifact persisted for this version.",
        examples=[{"artifact_id": "pa_abc12345", "status": "READY"}],
    )
    evidence_bundle: Dict[str, Any] = Field(
        default_factory=dict,
        description="Immutable evidence bundle JSON persisted for reproducibility.",
        examples=[{"hashes": {"request_hash": "sha256:abc", "artifact_hash": "sha256:def"}}],
    )
    gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Gate decision snapshot captured at version creation time.",
        examples=[
            {"gate": "CLIENT_CONSENT_REQUIRED", "recommended_next_step": "REQUEST_CLIENT_CONSENT"}
        ],
    )


class ProposalSummary(BaseModel):
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    portfolio_id: str = Field(description="Portfolio identifier.", examples=["pf_advisory_01"])
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier associated with the proposal.",
        examples=["mandate_growth_01"],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional jurisdiction code for policy context.",
        examples=["SG"],
    )
    created_by: str = Field(
        description="Actor id that created the proposal aggregate.",
        examples=["advisor_123"],
    )
    created_at: str = Field(
        description="UTC ISO8601 creation timestamp of proposal aggregate.",
        examples=["2026-02-19T12:00:00+00:00"],
    )
    last_event_at: str = Field(
        description="UTC ISO8601 timestamp of latest workflow event.",
        examples=["2026-02-19T12:05:00+00:00"],
    )
    current_state: ProposalWorkflowState = Field(
        description="Current workflow state derived from latest event.",
        examples=["DRAFT"],
    )
    current_version_no: int = Field(
        description="Current latest proposal version number.",
        examples=[1],
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing proposal title.",
        examples=["2026 client portfolio transition plan"],
    )
    lifecycle_origin: ProposalLifecycleOrigin = Field(
        description="How the advisory proposal first entered lifecycle ownership.",
        examples=["WORKSPACE_HANDOFF"],
    )
    source_workspace_id: Optional[str] = Field(
        default=None,
        description=(
            "Workspace identifier captured when lifecycle ownership started from a workspace."
        ),
        examples=["aws_001"],
    )


class ProposalCreateResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Created proposal aggregate summary.",
        examples=[{"proposal_id": "pp_001", "current_state": "DRAFT", "current_version_no": 1}],
    )
    version: ProposalVersionDetail = Field(
        description="Created immutable proposal version.",
        examples=[
            {"proposal_version_id": "ppv_001", "version_no": 1, "status_at_creation": "READY"}
        ],
    )
    latest_workflow_event: ProposalWorkflowEvent = Field(
        description="Latest workflow event emitted during create.",
        examples=[{"event_type": "CREATED", "to_state": "DRAFT"}],
    )


class ProposalDetailResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal aggregate summary.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTION_READY"}],
    )
    current_version: ProposalVersionDetail = Field(
        description="Current latest immutable proposal version.",
        examples=[{"proposal_version_id": "ppv_002", "version_no": 2}],
    )
    last_gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Gate decision from current version.",
        examples=[{"gate": "EXECUTION_READY", "recommended_next_step": "EXECUTE"}],
    )


class ProposalListResponse(BaseModel):
    items: List[ProposalSummary] = Field(
        default_factory=list,
        description="Paginated proposal summary rows.",
        examples=[[{"proposal_id": "pp_001", "portfolio_id": "pf_01", "current_state": "DRAFT"}]],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for pagination of subsequent pages.",
        examples=["pp_001"],
    )


class ProposalReportRequest(BaseModel):
    report_type: ProposalReportType = Field(
        description="Lotus-branded advisory report payload requested from lotus-report.",
        examples=["CLIENT_PROPOSAL_SUMMARY"],
    )
    requested_by: str = Field(
        description="Actor id requesting advisory report generation.",
        examples=["advisor_123"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description=(
            "Optional immutable proposal version number to anchor the reporting payload. "
            "Defaults to the current proposal version when omitted."
        ),
        examples=[1],
    )
    include_execution_summary: bool = Field(
        default=True,
        description=(
            "Whether advisory execution-state summary should be included in report context."
        ),
        examples=[True],
    )
    include_reviewed_narrative: bool = Field(
        default=False,
        description=(
            "Whether the request must include the immutable proposal narrative package. When "
            "true, lotus-advise blocks report generation unless the selected proposal version "
            "has a persisted narrative approved for advisor use and the review hash still "
            "matches the source narrative."
        ),
        examples=[True],
    )


class ProposalReportResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary used as advisory reporting context.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTION_READY"}],
    )
    report_request_id: str = Field(
        description="Advisory correlation id for the lotus-report request.",
        examples=["prr_001"],
    )
    report_type: ProposalReportType = Field(
        description="Lotus-branded report payload requested from lotus-report.",
        examples=["CLIENT_PROPOSAL_SUMMARY"],
    )
    report_service: str = Field(
        description="Authoritative downstream report service used for generation.",
        examples=["lotus-report"],
    )
    status: str = Field(
        description="Current report request status returned by the reporting seam.",
        examples=["READY"],
    )
    generated_at: str = Field(
        description="UTC ISO8601 timestamp when the report payload was generated.",
        examples=["2026-03-26T09:00:00+00:00"],
    )
    report_reference_id: str = Field(
        description="Opaque lotus-report reference id for downstream retrieval or audit.",
        examples=["lotus_report_artifact_001"],
    )
    artifact_url: Optional[str] = Field(
        default=None,
        description="Optional lotus-report artifact URL when available.",
        examples=["https://lotus-report.local/artifacts/lotus_report_artifact_001"],
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured advisory explanation of the report assembly and ownership boundary."
        ),
        examples=[
            {
                "ownership": "REPORTING_OWNED_BY_LOTUS_REPORT",
                "related_version_no": 1,
                "include_execution_summary": True,
            }
        ],
    )


class ProposalExecutionHandoffRequest(BaseModel):
    actor_id: str = Field(
        description="Actor id requesting execution handoff for the advisory proposal.",
        examples=["ops_001"],
    )
    execution_provider: str = Field(
        description="Execution venue or OMS receiving the handoff.",
        examples=["lotus-manage"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description=(
            "Optional immutable proposal version number being handed to execution. "
            "Defaults to the current version when omitted."
        ),
        examples=[1],
    )
    expected_state: Optional[ProposalWorkflowState] = Field(
        default=None,
        description="Optimistic concurrency check against the current lifecycle state.",
        examples=["EXECUTION_READY"],
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Optional correlation id propagated into advisory execution audit history.",
        examples=["corr-exec-handoff-001"],
    )
    external_request_id: Optional[str] = Field(
        default=None,
        description="Optional external execution request id supplied by the execution provider.",
        examples=["oms_req_001"],
    )
    notes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured advisory handoff notes captured for execution audit.",
        examples=[{"channel": "OMS", "priority": "STANDARD"}],
    )


class ProposalExecutionUpdateRequest(BaseModel):
    update_id: str = Field(
        description="Stable downstream execution update identifier used for idempotent ingestion.",
        examples=["exec_update_001"],
    )
    actor_id: str = Field(
        description="Actor or system identifier recording the downstream execution update.",
        examples=["lotus-manage"],
    )
    execution_request_id: str = Field(
        description="Advisory execution request identifier previously recorded at handoff.",
        examples=["oms_req_001"],
    )
    execution_provider: str = Field(
        description="Execution venue or OMS that produced the downstream update.",
        examples=["lotus-manage"],
    )
    update_status: ProposalExecutionUpdateStatus = Field(
        description="Normalized downstream execution posture being ingested.",
        examples=["PARTIALLY_EXECUTED"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Immutable proposal version number the downstream execution update applies to.",
        examples=[1],
    )
    external_execution_id: Optional[str] = Field(
        default=None,
        description="External downstream execution or ticket identifier when supplied.",
        examples=["oms_fill_001"],
    )
    occurred_at: Optional[str] = Field(
        default=None,
        description="Optional UTC ISO8601 timestamp supplied by the downstream execution system.",
        examples=["2026-03-26T09:10:00+00:00"],
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured downstream execution metadata preserved for audit and reconciliation."
        ),
        examples=[{"filled_quantity": "50", "remaining_quantity": "25"}],
    )


class ProposalExecutionHandoffResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary after execution handoff request processing.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTION_READY"}],
    )
    execution_request_id: str = Field(
        description="Advisory execution handoff correlation identifier.",
        examples=["pex_001"],
    )
    handoff_status: ProposalExecutionHandoffStatus = Field(
        description="Execution handoff status after the request is recorded.",
        examples=["REQUESTED"],
    )
    execution_provider: str = Field(
        description="Execution venue or OMS receiving the advisory handoff.",
        examples=["lotus-manage"],
    )
    execution_ownership: Dict[str, str] = Field(
        default_factory=execution_ownership_boundary,
        description=(
            "Explicit ownership boundary showing that lotus-advise records handoff posture "
            "while the downstream execution provider remains the system of record."
        ),
        examples=[
            {
                "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
            }
        ],
    )
    latest_workflow_event: ProposalWorkflowEvent = Field(
        description="Append-only workflow event created for the execution handoff.",
        examples=[{"event_type": "EXECUTION_REQUESTED", "to_state": "EXECUTION_READY"}],
    )


class ProposalExecutionStatusResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured at execution-status retrieval time.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTED"}],
    )
    handoff_status: ProposalExecutionHandoffStatus = Field(
        description="Derived advisory execution handoff status.",
        examples=["EXECUTED"],
    )
    execution_request_id: Optional[str] = Field(
        default=None,
        description="Latest advisory execution handoff identifier when a handoff was recorded.",
        examples=["pex_001"],
    )
    execution_provider: Optional[str] = Field(
        default=None,
        description="Execution venue or OMS associated with the latest handoff.",
        examples=["lotus-manage"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Immutable proposal version currently correlated to execution status.",
        examples=[1],
    )
    handoff_requested_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp of the latest execution handoff request.",
        examples=["2026-03-26T09:00:00+00:00"],
    )
    executed_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution completed, when known.",
        examples=["2026-03-26T09:15:00+00:00"],
    )
    external_execution_id: Optional[str] = Field(
        default=None,
        description="External execution identifier captured from advisory workflow events.",
        examples=["oms_fill_001"],
    )
    latest_workflow_event: Optional[ProposalWorkflowEvent] = Field(
        default=None,
        description="Latest execution-related workflow event correlated for advisory audit.",
        examples=[{"event_type": "EXECUTED", "to_state": "EXECUTED"}],
    )
    execution_ownership: Dict[str, str] = Field(
        default_factory=execution_ownership_boundary,
        description=(
            "Explicit ownership boundary for execution status projection; lotus-advise "
            "correlates advisory posture and downstream updates but does not own execution truth."
        ),
        examples=[
            {
                "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
            }
        ],
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured explanation of how advisory execution status was correlated.",
        examples=[
            {
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "state_correlation": "EXECUTION_REQUESTED_AND_EXECUTED_EVENTS",
                "execution_ownership": {
                    "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                    "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                    "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
                },
            }
        ],
    )


class ProposalDeliveryExecutionSummary(BaseModel):
    handoff_status: str = Field(
        description="Derived advisory execution handoff status.",
        examples=["EXECUTED"],
    )
    execution_request_id: Optional[str] = Field(
        default=None,
        description="Latest advisory execution request identifier when available.",
        examples=["oms_req_001"],
    )
    execution_provider: Optional[str] = Field(
        default=None,
        description="Execution venue or OMS associated with the latest delivery event.",
        examples=["lotus-manage"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Immutable proposal version currently correlated to delivery execution state.",
        examples=[1],
    )
    handoff_requested_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp of the latest execution handoff request.",
        examples=["2026-03-26T09:00:00+00:00"],
    )
    executed_at: Optional[str] = Field(
        default=None,
        description="UTC ISO8601 timestamp when execution completed, when known.",
        examples=["2026-03-26T09:15:00+00:00"],
    )
    latest_event_type: str = Field(
        description="Latest delivery event type used for execution summary correlation.",
        examples=["EXECUTED"],
    )
    external_execution_id: Optional[str] = Field(
        default=None,
        description="External execution identifier captured from downstream execution updates.",
        examples=["oms_fill_001"],
    )
    execution_ownership: Dict[str, str] = Field(
        default_factory=execution_ownership_boundary,
        description=(
            "Explicit ownership boundary for delivery execution posture; execution truth remains "
            "with the downstream provider."
        ),
        examples=[
            {
                "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
            }
        ],
    )


class ProposalDeliveryReportingSummary(BaseModel):
    report_request_id: str = Field(
        description="Advisory correlation id for the downstream report request.",
        examples=["prr_001"],
    )
    report_type: ProposalReportType = Field(
        description="Lotus-branded report payload requested from lotus-report.",
        examples=["CLIENT_PROPOSAL_SUMMARY"],
    )
    report_service: str = Field(
        description="Authoritative downstream report service used for generation.",
        examples=["lotus-report"],
    )
    status: str = Field(
        description="Current report request status returned by the reporting seam.",
        examples=["READY"],
    )
    report_reference_id: Optional[str] = Field(
        default=None,
        description="Opaque lotus-report reference id for downstream retrieval or audit.",
        examples=["lotus_report_artifact_001"],
    )
    artifact_url: Optional[str] = Field(
        default=None,
        description="Optional lotus-report artifact URL when available.",
        examples=["https://lotus-report.local/artifacts/lotus_report_artifact_001"],
    )
    requested_by: str = Field(
        description="Actor id that requested the downstream report generation.",
        examples=["advisor_123"],
    )
    related_version_no: Optional[int] = Field(
        default=None,
        description="Immutable proposal version the report request is anchored to.",
        examples=[1],
    )
    include_execution_summary: bool = Field(
        description="Whether the report request included advisory execution-state context.",
        examples=[True],
    )
    include_reviewed_narrative: bool = Field(
        default=False,
        description=(
            "Whether the report request included an approved, source-backed proposal narrative "
            "package for downstream report assembly."
        ),
        examples=[True],
    )
    proposal_narrative_package: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Compact lineage summary of the reviewed proposal narrative package included in "
            "the downstream report request, when requested."
        ),
        examples=[
            {
                "package_status": "INCLUDED_REVIEWED_NARRATIVE",
                "narrative_id": "pn_001",
                "review_id": "pwe_narrative_review_001",
                "review_state": "APPROVED_FOR_ADVISOR_USE",
                "source_narrative_hash": "sha256:abc123",
            }
        ],
    )
    generated_at: str = Field(
        description="UTC ISO8601 timestamp when the report payload was generated.",
        examples=["2026-03-26T09:00:00+00:00"],
    )


class ProposalDeliverySummaryResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured at delivery-summary retrieval time.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTED"}],
    )
    execution: Optional[ProposalDeliveryExecutionSummary] = Field(
        default=None,
        description=(
            "Normalized execution delivery summary derived from append-only workflow events."
        ),
    )
    reporting: Optional[ProposalDeliveryReportingSummary] = Field(
        default=None,
        description=(
            "Normalized reporting delivery summary derived from append-only workflow events."
        ),
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured explanation of how the delivery summary was assembled.",
        examples=[
            {
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "execution_ownership": {
                    "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                    "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                    "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
                },
            }
        ],
    )


class ProposalDeliveryHistoryResponse(BaseModel):
    proposal: ProposalSummary = Field(
        description="Proposal summary captured at delivery-history retrieval time.",
        examples=[{"proposal_id": "pp_001", "current_state": "EXECUTED"}],
    )
    event_count: int = Field(
        description="Number of delivery events returned in the filtered history payload.",
        examples=[3],
    )
    latest_event: Optional[ProposalWorkflowEvent] = Field(
        default=None,
        description="Latest delivery event in the append-only delivery timeline.",
        examples=[{"event_type": "REPORT_REQUESTED", "to_state": "EXECUTED"}],
    )
    events: List[ProposalWorkflowEvent] = Field(
        default_factory=list,
        description="Append-only delivery events ordered by event occurrence.",
        examples=[[{"event_type": "EXECUTION_REQUESTED", "to_state": "EXECUTION_READY"}]],
    )
    explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured explanation of how the delivery history was assembled.",
        examples=[
            {
                "source": "ADVISORY_WORKFLOW_EVENTS",
                "filter": "DELIVERY_ONLY",
                "execution_ownership": {
                    "advisory_role": "HANDOFF_REQUEST_AND_STATUS_RECONCILIATION",
                    "execution_system_of_record": "DOWNSTREAM_EXECUTION_PROVIDER",
                    "ownership_boundary": "DOWNSTREAM_EXECUTION_SYSTEM_OF_RECORD",
                },
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
