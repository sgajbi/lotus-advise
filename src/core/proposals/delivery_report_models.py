from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.core.proposals.contract_types import ProposalReportType
from src.core.proposals.lifecycle_response_models import ProposalSummary


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
        description="Current report request status returned by the reporting integration boundary.",
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
