from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)
from src.core.proposals.response_models import ProposalReportResponse


class PolicyEvaluationReportPackageRequest(BaseModel):
    requested_by: str = Field(
        description=(
            "Compatibility actor echo for report/render/archive materialization. The route "
            "authorizes and records the trusted policy checker principal from policy-control "
            "headers and rejects a mismatch."
        ),
        examples=["policy_checker_1"],
    )
    portfolio_id: str = Field(
        description="Portfolio identifier for the policy report package.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    source_evaluation_hash: str = Field(
        description="Immutable policy evaluation hash inspected by the requester.",
        examples=["sha256:policy-evaluation"],
    )
    requested_output_formats: list[str] = Field(
        default_factory=lambda: ["pdf"],
        min_length=1,
        description="Output formats requested from lotus-report for the policy package.",
        examples=[["pdf"]],
    )
    client_ready_document_requested: bool = Field(
        default=False,
        description=(
            "Whether the caller is requesting client-ready document release. This remains blocked "
            "by the RFC-0025 and RFC-0028 client-ready publication controls."
        ),
        examples=[False],
    )
    reason: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured report-package request reason retained in policy lineage.",
        examples=[{"purpose": "compliance sign-off package"}],
    )


class PolicyEvaluationReportPackageResponse(BaseModel):
    evaluation: PolicyEvaluationRecord = Field(
        description="Policy evaluation record after report-package event recording."
    )
    report_package_event: PolicyEvaluationAuditEvent = Field(
        description="Created or replayed report/render/archive reference event."
    )
    report: ProposalReportResponse = Field(
        description="lotus-report job handle and materialization references."
    )
    replayed: bool = Field(
        description="Whether this request replayed an existing idempotent report-package event.",
        examples=[False],
    )
