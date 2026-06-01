from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.gate_models import GateDecision
from src.core.proposal_result_models import ProposalResult
from src.core.proposals.contract_types import (
    ProposalApprovalType,
    ProposalCreationStatus,
    ProposalLifecycleOrigin,
    ProposalWorkflowEventType,
    ProposalWorkflowState,
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
    portfolio_id: str = Field(
        description="Portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
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
        examples=[
            [
                {
                    "proposal_id": "pp_001",
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "current_state": "DRAFT",
                }
            ]
        ],
    )
    next_cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for pagination of subsequent pages.",
        examples=["pp_001"],
    )
