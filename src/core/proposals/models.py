from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.models import GateDecision, ProposalResult, ProposalSimulateRequest

ProposalWorkflowState = Literal[
    "DRAFT",
    "RISK_REVIEW",
    "COMPLIANCE_REVIEW",
    "AWAITING_CLIENT_CONSENT",
    "EXECUTION_READY",
    "EXECUTED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
]

ProposalWorkflowEventType = Literal[
    "CREATED",
    "NEW_VERSION_CREATED",
    "SUBMITTED_FOR_RISK_REVIEW",
    "RISK_APPROVED",
    "SUBMITTED_FOR_COMPLIANCE_REVIEW",
    "COMPLIANCE_APPROVED",
    "CLIENT_CONSENT_RECORDED",
    "EXECUTION_REQUESTED",
    "EXECUTED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
]

ProposalApprovalType = Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"]
ProposalCreationStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED"]


class ProposalCreateMetadata(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="Optional advisor-facing proposal title.",
        examples=["2026 tactical rebalance plan"],
    )
    advisor_notes: Optional[str] = Field(
        default=None,
        description="Optional free-text advisor notes captured at proposal creation.",
        examples=["Client asked for controlled equity rotation with cash discipline."],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Optional proposal jurisdiction code.",
        examples=["SG"],
    )
    mandate_id: Optional[str] = Field(
        default=None,
        description="Optional mandate identifier for the proposal context.",
        examples=["mandate_growth_01"],
    )


class ProposalCreateRequest(BaseModel):
    created_by: str = Field(
        description="Actor id creating the proposal record.",
        examples=["advisor_123"],
    )
    simulate_request: ProposalSimulateRequest = Field(
        description="Full advisory simulation payload persisted as version evidence input.",
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )
    metadata: ProposalCreateMetadata = Field(
        default_factory=ProposalCreateMetadata,
        description="Optional proposal metadata persisted alongside proposal aggregate.",
        examples=[
            {
                "title": "2026 tactical rebalance plan",
                "advisor_notes": "Client requested medium-risk equity rotation.",
                "jurisdiction": "SG",
                "mandate_id": "mandate_growth_01",
            }
        ],
    )


class ProposalVersionRequest(BaseModel):
    created_by: str = Field(
        description="Actor id creating the new proposal version.",
        examples=["advisor_456"],
    )
    simulate_request: ProposalSimulateRequest = Field(
        description="Full advisory simulation payload for the new immutable version.",
        examples=[
            {
                "portfolio_snapshot": {
                    "portfolio_id": "pf_advisory_01",
                    "base_currency": "USD",
                },
                "market_data_snapshot": {"prices": [], "fx_rates": []},
                "shelf_entries": [],
                "options": {"enable_proposal_simulation": True},
                "proposed_cash_flows": [],
                "proposed_trades": [],
            }
        ],
    )


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
        examples=["2026 tactical rebalance plan"],
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
    versions: List[ProposalVersionLineageItem] = Field(
        default_factory=list,
        description="Immutable proposal version lineage ordered by version number ascending.",
    )


class ProposalWorkflowTimelineResponse(BaseModel):
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    current_state: ProposalWorkflowState = Field(
        description="Current workflow state at retrieval time.",
        examples=["AWAITING_CLIENT_CONSENT"],
    )
    events: List[ProposalWorkflowEvent] = Field(
        default_factory=list,
        description="Append-only workflow events ordered by event occurrence.",
    )


class ProposalApprovalsResponse(BaseModel):
    proposal_id: str = Field(description="Proposal identifier.", examples=["pp_001"])
    approvals: List[ProposalApprovalRecord] = Field(
        default_factory=list,
        description="Structured approval/consent records ordered by occurrence.",
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
    proposal_id: str = Field(description="Proposal identifier mapped by idempotency key.")
    proposal_version_no: int = Field(
        description="Proposal version number mapped by idempotency key.", examples=[1]
    )
    created_at: str = Field(
        description="UTC ISO8601 timestamp when idempotency mapping was persisted.",
        examples=["2026-02-19T12:00:00+00:00"],
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
        examples=["2026 tactical rebalance plan"],
    )
    advisor_notes: Optional[str] = Field(
        default=None,
        description="Internal advisor notes.",
        examples=["Client approved initial draft."],
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
