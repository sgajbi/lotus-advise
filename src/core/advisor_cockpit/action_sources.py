from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionFamily,
    AdvisorCockpitActionPriority,
    AdvisorCockpitActionStatus,
    AdvisorCockpitOwnerRole,
    AdvisorCockpitSlaAgeBand,
    AdvisorCockpitUnsupportedCapability,
    CockpitDependencyReadiness,
    CockpitEvidenceRef,
    CockpitLineageRef,
    CockpitSourceReadinessGap,
)


class CockpitActionSourceRefs(BaseModel):
    client_ref: str | None = Field(default=None, description="Source-backed client reference.")
    household_ref: str | None = Field(
        default=None, description="Source-backed household reference."
    )
    portfolio_id: str | None = Field(
        default=None,
        description="Source-backed portfolio identifier.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    proposal_id: str | None = Field(default=None, description="Source-backed proposal identifier.")
    workspace_id: str | None = Field(default=None, description="Source-backed workspace id.")
    memo_id: str | None = Field(default=None, description="Source-backed memo id.")
    policy_evaluation_id: str | None = Field(
        default=None, description="Source-backed policy evaluation id."
    )
    report_ref: str | None = Field(default=None, description="Source-backed report reference.")
    execution_ref: str | None = Field(
        default=None, description="Source-backed execution handoff or status reference."
    )


class CockpitActionConstructionInput(BaseModel):
    source_action_id: str = Field(
        description="Stable source id used to derive the cockpit action identity.",
        examples=["policy_eval_sg_001"],
    )
    action_family: AdvisorCockpitActionFamily = Field(
        description="Business action family assigned by the Advise cockpit domain."
    )
    status: AdvisorCockpitActionStatus = Field(
        description="Backend-owned action posture to render in Workbench."
    )
    priority: AdvisorCockpitActionPriority = Field(
        description="Backend-owned deterministic action priority."
    )
    owner_role: AdvisorCockpitOwnerRole = Field(
        description="Role that owns the next step or external handoff."
    )
    title: str = Field(description="Business-facing action title.")
    next_required_action: str = Field(description="Backend-owned next required action.")
    reason_codes: list[str] = Field(
        description="Stable machine-readable reason codes explaining the action."
    )
    source_refs: CockpitActionSourceRefs = Field(
        default_factory=CockpitActionSourceRefs,
        description="Source-backed entity references carried into the action.",
    )
    due_at: str | None = Field(default=None, description="UTC ISO8601 due timestamp.")
    sla_age_band: AdvisorCockpitSlaAgeBand = Field(
        default="NOT_APPLICABLE", description="Backend-owned SLA aging posture."
    )
    materiality_rank: int = Field(
        default=0,
        ge=0,
        description="Bounded materiality rank used for deterministic ordering.",
    )
    source_timestamp: str | None = Field(
        default=None, description="UTC ISO8601 source event or evidence timestamp."
    )
    evidence_refs: list[CockpitEvidenceRef] = Field(default_factory=list)
    source_readiness_gaps: list[CockpitSourceReadinessGap] = Field(default_factory=list)
    dependency_readiness: list[CockpitDependencyReadiness] = Field(default_factory=list)
    lineage_refs: list[CockpitLineageRef] = Field(default_factory=list)
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = Field(
        default_factory=list
    )
    correlation_id: str | None = Field(default=None, description="Caller/source correlation id.")


class PolicyReviewActionSource(BaseModel):
    policy_evaluation_id: str = Field(examples=["policy_eval_sg_001"])
    portfolio_id: str = Field(examples=["PB_SG_GLOBAL_BAL_001"])
    proposal_id: str | None = Field(default=None)
    policy_result: Literal["PENDING_REVIEW", "BLOCKED"] = Field(
        description="Supported policy posture that requires cockpit attention."
    )
    client_ready_posture: Literal["BLOCKED"] = Field(
        default="BLOCKED",
        description="Policy-driven client-ready posture; RFC-0026 must not upgrade it.",
    )
    summary: str = Field(
        default="Policy evaluation requires compliance review before advisor follow-up."
    )
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=80, ge=0)
    lineage_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    correlation_id: str | None = Field(default=None)


class MemoPackageBlockedActionSource(BaseModel):
    memo_id: str = Field(examples=["memo_sg_001"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    blockage_code: str = Field(examples=["MEMO_REVIEW_REQUIRED"])
    summary: str = Field(
        default="Proposal memo package is blocked until source evidence is reviewed."
    )
    owner_role: AdvisorCockpitOwnerRole = Field(default="REPORTING_OWNER")
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=60, ge=0)
    lineage_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    correlation_id: str | None = Field(default=None)


class MeetingPreparationActionSource(BaseModel):
    preparation_id: str = Field(examples=["prep_pb_sg_global_bal_001"])
    context_ref: str = Field(examples=["PB_SG_GLOBAL_BAL_001"])
    context_type: Literal["PORTFOLIO", "PROPOSAL", "CLIENT", "HOUSEHOLD"] = "PORTFOLIO"
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    proposal_id: str | None = Field(default=None)
    summary: str = Field(default="Meeting preparation packet is ready for advisor review.")
    evidence_refs: list[CockpitEvidenceRef] = Field(default_factory=list)
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=30, ge=0)
    correlation_id: str | None = Field(default=None)


class ClientFollowUpActionSource(BaseModel):
    follow_up_id: str = Field(examples=["follow_up_proposal_sg_001"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    follow_up_code: str = Field(examples=["CLIENT_CONSENT_FOLLOW_UP_REQUIRED"])
    summary: str = Field(
        default=(
            "Advisor follow-up is required before the proposal can progress. External client "
            "communication remains outside the cockpit boundary."
        )
    )
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=55, ge=0)
    correlation_id: str | None = Field(default=None)


class ApprovalDependencyActionSource(BaseModel):
    dependency_id: str = Field(examples=["approval_dependency_proposal_sg_001_compliance"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"] = Field(
        description="Proposal lifecycle approval or consent dependency."
    )
    approval_status: Literal["PENDING", "REJECTED"] = Field(
        description="Deterministic posture from proposal state and persisted approval records."
    )
    summary: str = Field(default="Proposal lifecycle approval dependency requires owner attention.")
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=72, ge=0)
    correlation_id: str | None = Field(default=None)


class ReportRenderArchiveActionSource(BaseModel):
    readiness_id: str = Field(examples=["report_archive_readiness_memo_sg_001"])
    memo_id: str = Field(examples=["memo_sg_001"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    readiness_code: str = Field(examples=["REPORT_PACKAGE_NOT_REQUESTED"])
    summary: str = Field(default="Report/render/archive readiness requires owner attention.")
    owner_role: AdvisorCockpitOwnerRole = Field(default="REPORTING_OWNER")
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=58, ge=0)
    lineage_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    correlation_id: str | None = Field(default=None)


class ExecutionHandoffReadyActionSource(BaseModel):
    handoff_id: str = Field(examples=["execution_handoff_ready_proposal_sg_001"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    summary: str = Field(default="Proposal is ready for execution handoff request.")
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=62, ge=0)
    correlation_id: str | None = Field(default=None)


class ExecutionStatusAttentionActionSource(BaseModel):
    execution_ref: str = Field(examples=["execution_request_sg_001"])
    proposal_id: str = Field(examples=["proposal_sg_001"])
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    handoff_status: Literal[
        "REQUESTED",
        "ACCEPTED",
        "PARTIALLY_EXECUTED",
        "REJECTED",
        "CANCELLED",
        "EXPIRED",
    ] = Field(description="Source-backed execution handoff/status posture.")
    summary: str = Field(default="Execution handoff status requires advisor cockpit attention.")
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=64, ge=0)
    correlation_id: str | None = Field(default=None)


class HouseViewImpactActionSource(BaseModel):
    cohort_id: str = Field(examples=["thv_cohort_sg_001"])
    tactical_view_id: str = Field(examples=["thv_2026_05_asia_duration"])
    tactical_view_version: str = Field(examples=["2026.05"])
    portfolio_id: str = Field(examples=["PB_SG_GLOBAL_BAL_001"])
    impact_code: str = Field(examples=["TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"])
    summary: str = Field(default="Portfolio is affected by a source-backed tactical house view.")
    lineage_id: str | None = Field(default=None)
    content_hash: str | None = Field(default=None)
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=52, ge=0)
    correlation_id: str | None = Field(default=None)


class SupportabilityDegradedActionSource(BaseModel):
    dependency: str = Field(examples=["lotus-report"])
    state: Literal["DEGRADED", "UNAVAILABLE", "NOT_CONFIGURED"] = Field(
        description="Dependency state that affects cockpit readiness."
    )
    reason_code: str = Field(examples=["REPORT_PACKAGE_UNAVAILABLE"])
    summary: str = Field(
        default="A source dependency is degraded; cockpit evidence is not fully ready."
    )
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    due_at: str | None = Field(default=None)
    source_timestamp: str | None = Field(default=None)
    materiality_rank: int = Field(default=40, ge=0)
    correlation_id: str | None = Field(default=None)


class UnsupportedCapabilityActionSource(BaseModel):
    capability: AdvisorCockpitUnsupportedCapability = Field(examples=["CLIENT_READY_PUBLICATION"])
    context_ref: str = Field(examples=["PB_SG_GLOBAL_BAL_001"])
    reason_code: str = Field(examples=["CLIENT_READY_PUBLICATION_NOT_SUPPORTED"])
    summary: str = Field(
        default="This cockpit capability is not implementation-backed and must not be claimed."
    )
    portfolio_id: str | None = Field(default=None, examples=["PB_SG_GLOBAL_BAL_001"])
    source_timestamp: str | None = Field(default=None)
    correlation_id: str | None = Field(default=None)
