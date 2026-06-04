from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from src.core.proposals.memo_types import (
    ProposalMemoCommentarySection,
    ProposalMemoLifecycleStatus,
    ProposalMemoReportOutputFormat,
    ProposalMemoReportPackageStatus,
    ProposalMemoReviewAction,
)


class ProposalMemoCreateRequest(BaseModel):
    created_by: str = Field(
        description="Actor creating or replaying the advisor proposal memo.",
        examples=["advisor_123"],
    )
    lifecycle_status: ProposalMemoLifecycleStatus = Field(
        default="DRAFT",
        description=(
            "Requested durable memo lifecycle status. `FINALIZED` is accepted only when the "
            "memo evidence pack is source-ready."
        ),
        examples=["DRAFT"],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured creation reason retained in memo audit evidence.",
        examples=[{"purpose": "Advisor review pack for client meeting."}],
    )


class ProposalMemoReviewRequest(BaseModel):
    action: ProposalMemoReviewAction = Field(
        description="Review action being recorded for the persisted memo.",
        examples=["APPROVE_FOR_ADVISOR_USE"],
    )
    reviewed_by: str = Field(description="Reviewer actor id.", examples=["compliance_001"])
    reason: str = Field(
        description="Business reason for the review decision.",
        examples=[
            "Memo is ready for advisor discussion; client-ready publication remains blocked."
        ],
    )
    source_memo_hash: str = Field(
        description="Memo hash the reviewer inspected; stale hashes are rejected.",
        examples=["sha256:memo"],
    )
    client_ready_release_requested: bool = Field(
        default=False,
        description=(
            "Whether the review attempts to release the memo for client-ready use. This remains "
            "unsupported in the current advisor-use memo contract."
        ),
        examples=[False],
    )


class ProposalMemoReportPackageEventRequest(BaseModel):
    recorded_by: str = Field(
        description="Actor recording report-package posture for the memo.",
        examples=["ops_001"],
    )
    report_package_id: str = Field(
        description="Downstream report-package or correlation identifier.",
        examples=["memo_report_package_001"],
    )
    report_package_status: ProposalMemoReportPackageStatus = Field(
        description="Report-package event posture.",
        examples=["BLOCKED"],
    )
    source_memo_hash: str = Field(
        description="Memo hash used by the report-package process; stale hashes are rejected.",
        examples=["sha256:memo"],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured report-package reason and downstream references.",
        examples=[{"blocked_by": "CLIENT_READY_MEMO_NOT_SUPPORTED"}],
    )


class ProposalMemoReportPackageRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting memo report/render/archive materialization.",
        examples=["advisor_123"],
    )
    source_memo_hash: str = Field(
        description=(
            "Memo hash inspected by the report-package requester; stale hashes are rejected."
        ),
        examples=["sha256:memo"],
    )
    requested_output_formats: list[ProposalMemoReportOutputFormat] = Field(
        default_factory=lambda: ["pdf"],
        min_length=1,
        description="Output formats requested from lotus-report for the memo package.",
        examples=[["pdf"]],
    )
    client_ready_document_requested: bool = Field(
        default=False,
        description=(
            "Whether the caller is requesting client-ready document release. This remains blocked "
            "until explicit client-ready document publication authority is supported."
        ),
        examples=[False],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured report-package request reason retained in memo lineage.",
        examples=[{"purpose": "advisor-use memo report package"}],
    )


class ProposalMemoAiCommentaryRequest(BaseModel):
    requested_by: str = Field(
        description="Actor requesting review-gated AI memo commentary.",
        examples=["advisor_123"],
    )
    source_memo_hash: str = Field(
        description="Memo hash inspected by the requester; stale hashes are rejected.",
        examples=["sha256:memo"],
    )
    requested_sections: list[ProposalMemoCommentarySection] = Field(
        default_factory=lambda: ["EXECUTIVE_SUMMARY", "LIMITATIONS_AND_DISCLOSURES"],
        min_length=1,
        description="Bounded advisor-use commentary sections requested from lotus-ai.",
        examples=[["EXECUTIVE_SUMMARY", "LIMITATIONS_AND_DISCLOSURES"]],
    )
    reason: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured request reason retained in memo AI lineage.",
        examples=[{"purpose": "advisor-use commentary draft"}],
    )


__all__ = [
    "ProposalMemoAiCommentaryRequest",
    "ProposalMemoCreateRequest",
    "ProposalMemoReportPackageEventRequest",
    "ProposalMemoReportPackageRequest",
    "ProposalMemoReviewRequest",
]
