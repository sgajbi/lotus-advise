from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import (
    ProposalExecutionHandoffStatus,
    ProposalExecutionUpdateStatus,
    ProposalWorkflowState,
)
from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.lifecycle_response_models import (
    ProposalSummary,
    ProposalWorkflowEvent,
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
