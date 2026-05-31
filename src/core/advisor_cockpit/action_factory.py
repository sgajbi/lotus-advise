from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypeVar, cast

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionFamily,
    AdvisorCockpitActionPriority,
    AdvisorCockpitActionStatus,
    AdvisorCockpitOwnerRole,
    AdvisorCockpitSlaAgeBand,
    AdvisorCockpitUnsupportedCapability,
    AdvisoryActionItem,
    CockpitDependencyReadiness,
    CockpitEvidenceRef,
    CockpitLineageRef,
    CockpitSourceReadinessGap,
)
from src.core.advisor_cockpit.vocabulary import sort_cockpit_action_items

LOTUS_ADVISE_SOURCE_SYSTEM = "lotus-advise"
T = TypeVar("T")


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


def build_source_backed_action(source: CockpitActionConstructionInput) -> AdvisoryActionItem:
    if not source.reason_codes:
        raise ValueError("cockpit action construction requires at least one reason code")
    if not (
        source.evidence_refs
        or source.source_readiness_gaps
        or source.dependency_readiness
        or source.unsupported_capabilities
    ):
        raise ValueError(
            "cockpit action construction requires evidence, readiness, dependency, "
            "or unsupported-capability context"
        )

    action_item_id = _build_action_item_id(source.action_family, source.source_action_id)
    return AdvisoryActionItem(
        action_item_id=action_item_id,
        action_item_version=1,
        action_family=source.action_family,
        status=source.status,
        priority=source.priority,
        owner_role=source.owner_role,
        owning_system=LOTUS_ADVISE_SOURCE_SYSTEM,
        title=source.title,
        next_required_action=source.next_required_action,
        reason_codes=_unique_ordered(source.reason_codes),
        client_ref=source.source_refs.client_ref,
        household_ref=source.source_refs.household_ref,
        portfolio_id=source.source_refs.portfolio_id,
        proposal_id=source.source_refs.proposal_id,
        workspace_id=source.source_refs.workspace_id,
        memo_id=source.source_refs.memo_id,
        policy_evaluation_id=source.source_refs.policy_evaluation_id,
        report_ref=source.source_refs.report_ref,
        execution_ref=source.source_refs.execution_ref,
        due_at=source.due_at,
        sla_age_band=source.sla_age_band,
        materiality_rank=source.materiality_rank,
        source_timestamp=source.source_timestamp,
        evidence_refs=source.evidence_refs,
        source_readiness_gaps=source.source_readiness_gaps,
        dependency_readiness=source.dependency_readiness,
        lineage_refs=source.lineage_refs
        or _lineage_refs(f"{source.action_family.lower()}:{source.source_action_id}", None),
        unsupported_capabilities=_unique_ordered(source.unsupported_capabilities),
        correlation_id=source.correlation_id,
    )


def build_policy_review_required_action(
    source: PolicyReviewActionSource,
) -> AdvisoryActionItem:
    status: AdvisorCockpitActionStatus = (
        "PENDING_REVIEW" if source.policy_result == "PENDING_REVIEW" else "BLOCKED"
    )
    reason_codes = ["POLICY_PENDING_REVIEW", "CLIENT_READY_BLOCKED"]
    if source.policy_result == "BLOCKED":
        reason_codes = ["POLICY_BLOCKED", "CLIENT_READY_BLOCKED"]

    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.policy_evaluation_id,
            action_family="POLICY_REVIEW_REQUIRED",
            status=status,
            priority="HIGH",
            owner_role="COMPLIANCE_REVIEWER",
            title="Policy review required",
            next_required_action=(
                "Review the policy evaluation before advisor follow-up or client-ready release."
            ),
            reason_codes=reason_codes,
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                policy_evaluation_id=source.policy_evaluation_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.policy_evaluation_id,
                    evidence_type="POLICY_EVALUATION",
                    summary=source.summary,
                    access_class="RESTRICTED_CUSTOMER_EVIDENCE",
                )
            ],
            source_readiness_gaps=[
                CockpitSourceReadinessGap(
                    source_family="policy",
                    gap_code=reason_codes[0],
                    owner_role="COMPLIANCE_REVIEWER",
                    message=(
                        "Policy review must be resolved before the proposal can become "
                        "client-ready."
                    ),
                )
            ],
            lineage_refs=_lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=[
                "CLIENT_READY_PUBLICATION",
                "COMPLETED_POLICY_APPROVAL_AUTHORITY",
                "COMPLETED_POLICY_SIGN_OFF_AUTHORITY",
            ],
            correlation_id=source.correlation_id,
        )
    )


def build_memo_package_blocked_action(
    source: MemoPackageBlockedActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.memo_id,
            action_family="MEMO_PACKAGE_BLOCKED",
            status="BLOCKED",
            priority="HIGH",
            owner_role=source.owner_role,
            title="Memo package blocked",
            next_required_action="Resolve the memo evidence gap before advisor-use packaging.",
            reason_codes=[source.blockage_code, "CLIENT_READY_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                memo_id=source.memo_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.memo_id,
                    evidence_type="PROPOSAL_MEMO",
                    summary=source.summary,
                    access_class="RESTRICTED_CUSTOMER_EVIDENCE",
                )
            ],
            source_readiness_gaps=[
                CockpitSourceReadinessGap(
                    source_family="proposal_memo",
                    gap_code=source.blockage_code,
                    owner_role=source.owner_role,
                    message="Memo source evidence must be resolved before packaging continues.",
                )
            ],
            lineage_refs=_lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=["CLIENT_READY_PUBLICATION"],
            correlation_id=source.correlation_id,
        )
    )


def build_meeting_preparation_action(
    source: MeetingPreparationActionSource,
) -> AdvisoryActionItem:
    portfolio_id = source.portfolio_id
    if source.context_type == "PORTFOLIO" and portfolio_id is None:
        portfolio_id = source.context_ref

    evidence_refs = source.evidence_refs or [
        _evidence_ref(
            evidence_id=source.preparation_id,
            evidence_type="MEETING_PREPARATION_PACKET",
            summary=source.summary,
            access_class="CUSTOMER_CONSUMABLE_SUMMARY",
        )
    ]
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.preparation_id,
            action_family="CLIENT_MEETING_PREPARATION",
            status="READY",
            priority="MEDIUM",
            owner_role="ADVISOR",
            title="Meeting preparation ready",
            next_required_action="Review the meeting preparation packet before client discussion.",
            reason_codes=["MEETING_PREPARATION_READY"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=evidence_refs,
            correlation_id=source.correlation_id,
        )
    )


def build_client_follow_up_action(
    source: ClientFollowUpActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.follow_up_id,
            action_family="CLIENT_FOLLOW_UP_REQUIRED",
            status="READY",
            priority="HIGH",
            owner_role="ADVISOR",
            title="Client follow-up required",
            next_required_action=(
                "Review the source-backed follow-up requirement before taking any client action."
            ),
            reason_codes=[source.follow_up_code, "EXTERNAL_CLIENT_COMMUNICATION_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.follow_up_id,
                    evidence_type="CLIENT_FOLLOW_UP_REQUIREMENT",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                CockpitSourceReadinessGap(
                    source_family="proposal_lifecycle",
                    gap_code=source.follow_up_code,
                    owner_role="ADVISOR",
                    message=source.summary,
                )
            ],
            unsupported_capabilities=["EXTERNAL_CLIENT_COMMUNICATION", "CRM_SYSTEM_OF_RECORD"],
            correlation_id=source.correlation_id,
        )
    )


def build_approval_dependency_action(
    source: ApprovalDependencyActionSource,
) -> AdvisoryActionItem:
    action_family: AdvisorCockpitActionFamily = (
        "CLIENT_CONSENT_REQUIRED"
        if source.approval_type == "CLIENT_CONSENT"
        else "APPROVAL_DEPENDENCY_AGING"
    )
    owner_role = _approval_owner_role(source.approval_type)
    pending_reason = f"{source.approval_type}_APPROVAL_PENDING"
    reason_codes = (
        [f"{source.approval_type}_APPROVAL_REJECTED", "CLIENT_READY_BLOCKED"]
        if source.approval_status == "REJECTED"
        else [pending_reason, "CLIENT_READY_BLOCKED"]
    )
    unsupported_capabilities: list[AdvisorCockpitUnsupportedCapability] = [
        "CLIENT_READY_PUBLICATION",
        "COMPLETED_POLICY_APPROVAL_AUTHORITY",
    ]
    if source.approval_type == "CLIENT_CONSENT":
        unsupported_capabilities = [
            "EXTERNAL_CLIENT_COMMUNICATION",
            "CRM_SYSTEM_OF_RECORD",
        ]

    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.dependency_id,
            action_family=action_family,
            status="BLOCKED" if source.approval_status == "REJECTED" else "PENDING_REVIEW",
            priority="CRITICAL" if source.approval_status == "REJECTED" else "HIGH",
            owner_role=owner_role,
            title=_approval_action_title(source.approval_type),
            next_required_action=_approval_next_required_action(source.approval_type),
            reason_codes=reason_codes,
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.dependency_id,
                    evidence_type="PROPOSAL_APPROVAL_DEPENDENCY",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                CockpitSourceReadinessGap(
                    source_family="proposal_lifecycle",
                    gap_code=reason_codes[0],
                    owner_role=owner_role,
                    message=source.summary,
                )
            ],
            unsupported_capabilities=unsupported_capabilities,
            correlation_id=source.correlation_id,
        )
    )


def build_report_render_archive_action(
    source: ReportRenderArchiveActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.readiness_id,
            action_family="REPORT_RENDER_ARCHIVE_BLOCKED",
            status="BLOCKED",
            priority="HIGH",
            owner_role=source.owner_role,
            title="Report and archive readiness blocked",
            next_required_action=(
                "Resolve report/render/archive readiness before presenting completed packaging."
            ),
            reason_codes=[source.readiness_code, "CLIENT_READY_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                memo_id=source.memo_id,
                report_ref=source.readiness_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.readiness_id,
                    evidence_type="REPORT_RENDER_ARCHIVE_READINESS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            source_readiness_gaps=[
                CockpitSourceReadinessGap(
                    source_family="report_render_archive",
                    gap_code=source.readiness_code,
                    owner_role=source.owner_role,
                    message=source.summary,
                )
            ],
            lineage_refs=_lineage_refs(source.lineage_id, source.content_hash),
            unsupported_capabilities=["CLIENT_READY_PUBLICATION"],
            correlation_id=source.correlation_id,
        )
    )


def build_execution_handoff_ready_action(
    source: ExecutionHandoffReadyActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.handoff_id,
            action_family="EXECUTION_HANDOFF_READY",
            status="READY",
            priority="MEDIUM",
            owner_role="EXECUTION_OWNER",
            title="Execution handoff ready",
            next_required_action=(
                "Request execution handoff through the governed Advise execution boundary."
            ),
            reason_codes=["EXECUTION_HANDOFF_READY", "OMS_ORDER_LIFECYCLE_BLOCKED"],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                execution_ref=source.handoff_id,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.handoff_id,
                    evidence_type="PROPOSAL_EXECUTION_HANDOFF_READINESS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            unsupported_capabilities=["OMS_ORDER_LIFECYCLE"],
            correlation_id=source.correlation_id,
        )
    )


def build_execution_status_attention_action(
    source: ExecutionStatusAttentionActionSource,
) -> AdvisoryActionItem:
    is_blocking = source.handoff_status in {"REJECTED", "CANCELLED", "EXPIRED"}
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.execution_ref,
            action_family="EXECUTION_STATUS_ATTENTION",
            status="BLOCKED" if is_blocking else "PENDING_REVIEW",
            priority="HIGH" if is_blocking else "MEDIUM",
            owner_role="EXECUTION_OWNER",
            title="Execution status attention",
            next_required_action=(
                "Review downstream execution posture without treating Advise as the OMS."
            ),
            reason_codes=[
                f"EXECUTION_STATUS_{source.handoff_status}",
                "OMS_ORDER_LIFECYCLE_BLOCKED",
            ],
            source_refs=CockpitActionSourceRefs(
                portfolio_id=source.portfolio_id,
                proposal_id=source.proposal_id,
                execution_ref=source.execution_ref,
            ),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.execution_ref,
                    evidence_type="PROPOSAL_EXECUTION_STATUS",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            unsupported_capabilities=["OMS_ORDER_LIFECYCLE"],
            correlation_id=source.correlation_id,
        )
    )


def build_house_view_impact_action(source: HouseViewImpactActionSource) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.cohort_id,
            action_family="HOUSE_VIEW_IMPACT_REVIEW",
            status="PENDING_REVIEW",
            priority="MEDIUM",
            owner_role="DPM_OWNER",
            title="Tactical house-view impact review",
            next_required_action=(
                "Review the source-backed tactical house-view cohort before DPM actioning."
            ),
            reason_codes=[source.impact_code, "TACTICAL_HOUSE_VIEW_REVIEW_REQUIRED"],
            source_refs=CockpitActionSourceRefs(portfolio_id=source.portfolio_id),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            evidence_refs=[
                _evidence_ref(
                    evidence_id=source.cohort_id,
                    evidence_type="TACTICAL_HOUSE_VIEW_COHORT",
                    summary=source.summary,
                    access_class="CUSTOMER_CONSUMABLE_SUMMARY",
                )
            ],
            lineage_refs=_lineage_refs(
                source.lineage_id or f"tactical_house_view_cohort:{source.cohort_id}",
                source.content_hash,
            ),
            correlation_id=source.correlation_id,
        )
    )


def build_supportability_degraded_action(
    source: SupportabilityDegradedActionSource,
) -> AdvisoryActionItem:
    is_blocking = source.state in {"UNAVAILABLE", "NOT_CONFIGURED"}
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=f"{source.dependency}_{source.reason_code}",
            action_family="SUPPORTABILITY_DEGRADED",
            status="BLOCKED" if is_blocking else "PENDING_REVIEW",
            priority="HIGH" if is_blocking else "MEDIUM",
            owner_role="SYSTEM",
            title="Cockpit source supportability attention",
            next_required_action="Review source readiness before relying on the cockpit posture.",
            reason_codes=[source.reason_code, f"DEPENDENCY_{source.state}"],
            source_refs=CockpitActionSourceRefs(portfolio_id=source.portfolio_id),
            due_at=source.due_at,
            sla_age_band="DUE_SOON" if source.due_at else "NOT_APPLICABLE",
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            dependency_readiness=[
                CockpitDependencyReadiness(
                    dependency=source.dependency,
                    state=source.state,
                    reason_code=source.reason_code,
                    summary=source.summary,
                )
            ],
            correlation_id=source.correlation_id,
        )
    )


def build_unsupported_capability_action(
    source: UnsupportedCapabilityActionSource,
) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=f"{source.context_ref}_{source.capability}",
            action_family="UNSUPPORTED_CAPABILITY",
            status="BLOCKED",
            priority="INFORMATIONAL",
            owner_role="SYSTEM",
            title="Unsupported cockpit capability",
            next_required_action="Do not present this capability as supported.",
            reason_codes=[source.reason_code],
            source_refs=CockpitActionSourceRefs(portfolio_id=source.portfolio_id),
            source_timestamp=source.source_timestamp,
            unsupported_capabilities=[source.capability],
            correlation_id=source.correlation_id,
        )
    )


def build_source_backed_cockpit_actions(
    *,
    policy_reviews: Sequence[PolicyReviewActionSource] = (),
    memo_blocks: Sequence[MemoPackageBlockedActionSource] = (),
    meeting_preparations: Sequence[MeetingPreparationActionSource] = (),
    client_follow_ups: Sequence[ClientFollowUpActionSource] = (),
    approval_dependencies: Sequence[ApprovalDependencyActionSource] = (),
    report_render_archive_items: Sequence[ReportRenderArchiveActionSource] = (),
    execution_handoffs: Sequence[ExecutionHandoffReadyActionSource] = (),
    execution_status_items: Sequence[ExecutionStatusAttentionActionSource] = (),
    house_view_impacts: Sequence[HouseViewImpactActionSource] = (),
    supportability_events: Sequence[SupportabilityDegradedActionSource] = (),
    unsupported_capabilities: Sequence[UnsupportedCapabilityActionSource] = (),
) -> list[AdvisoryActionItem]:
    actions = [
        *(build_policy_review_required_action(source) for source in policy_reviews),
        *(build_memo_package_blocked_action(source) for source in memo_blocks),
        *(build_meeting_preparation_action(source) for source in meeting_preparations),
        *(build_client_follow_up_action(source) for source in client_follow_ups),
        *(build_approval_dependency_action(source) for source in approval_dependencies),
        *(build_report_render_archive_action(source) for source in report_render_archive_items),
        *(build_execution_handoff_ready_action(source) for source in execution_handoffs),
        *(build_execution_status_attention_action(source) for source in execution_status_items),
        *(build_house_view_impact_action(source) for source in house_view_impacts),
        *(build_supportability_degraded_action(source) for source in supportability_events),
        *(build_unsupported_capability_action(source) for source in unsupported_capabilities),
    ]
    return cast(list[AdvisoryActionItem], sort_cockpit_action_items(actions))


def _build_action_item_id(action_family: str, source_action_id: str) -> str:
    return f"aci_{_normalize_identifier(action_family)}_{_normalize_identifier(source_action_id)}"


def _normalize_identifier(value: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    return "_".join(part for part in normalized.split("_") if part)


def _evidence_ref(
    *,
    evidence_id: str,
    evidence_type: str,
    summary: str,
    access_class: Literal[
        "CUSTOMER_CONSUMABLE_SUMMARY",
        "RESTRICTED_CUSTOMER_EVIDENCE",
        "OPERATOR_ONLY_SUPPORTABILITY",
        "INTERNAL_ONLY_DIAGNOSTICS",
    ],
) -> CockpitEvidenceRef:
    return CockpitEvidenceRef(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_system=LOTUS_ADVISE_SOURCE_SYSTEM,
        access_class=access_class,
        summary=summary,
    )


def _lineage_refs(lineage_id: str | None, content_hash: str | None) -> list[CockpitLineageRef]:
    if lineage_id is None:
        return []
    return [
        CockpitLineageRef(
            lineage_id=lineage_id,
            source_system=LOTUS_ADVISE_SOURCE_SYSTEM,
            content_hash=content_hash,
        )
    ]


def _approval_owner_role(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> AdvisorCockpitOwnerRole:
    if approval_type == "RISK":
        return "INVESTMENT_DESK"
    if approval_type == "COMPLIANCE":
        return "COMPLIANCE_REVIEWER"
    return "ADVISOR"


def _approval_action_title(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> str:
    if approval_type == "RISK":
        return "Risk review pending"
    if approval_type == "COMPLIANCE":
        return "Compliance review pending"
    return "Client consent required"


def _approval_next_required_action(
    approval_type: Literal["RISK", "COMPLIANCE", "CLIENT_CONSENT"],
) -> str:
    if approval_type == "RISK":
        return "Review the proposal risk dependency before client consent can progress."
    if approval_type == "COMPLIANCE":
        return "Review the compliance dependency before client consent can progress."
    return "Record source-backed consent posture before execution readiness can change."


def _unique_ordered(values: Sequence[T]) -> list[T]:
    unique: list[T] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
