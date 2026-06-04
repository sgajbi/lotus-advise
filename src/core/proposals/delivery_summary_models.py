from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import ProposalReportType
from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.lifecycle_response_models import (
    ProposalSummary,
    ProposalWorkflowEvent,
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
        description="Current report request status returned by the reporting integration boundary.",
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
