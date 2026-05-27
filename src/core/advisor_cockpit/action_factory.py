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
        lineage_refs=source.lineage_refs,
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


def build_first_wave_cockpit_actions(
    *,
    policy_reviews: Sequence[PolicyReviewActionSource] = (),
    memo_blocks: Sequence[MemoPackageBlockedActionSource] = (),
    meeting_preparations: Sequence[MeetingPreparationActionSource] = (),
    client_follow_ups: Sequence[ClientFollowUpActionSource] = (),
    supportability_events: Sequence[SupportabilityDegradedActionSource] = (),
    unsupported_capabilities: Sequence[UnsupportedCapabilityActionSource] = (),
) -> list[AdvisoryActionItem]:
    actions = [
        *(build_policy_review_required_action(source) for source in policy_reviews),
        *(build_memo_package_blocked_action(source) for source in memo_blocks),
        *(build_meeting_preparation_action(source) for source in meeting_preparations),
        *(build_client_follow_up_action(source) for source in client_follow_ups),
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


def _unique_ordered(values: Sequence[T]) -> list[T]:
    unique: list[T] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
