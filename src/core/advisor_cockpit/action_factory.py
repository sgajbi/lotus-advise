from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from src.core.advisor_cockpit import action_components
from src.core.advisor_cockpit.action_advisor_workflow import (
    build_client_follow_up_action,
    build_meeting_preparation_action,
)
from src.core.advisor_cockpit.action_approval import build_approval_dependency_action
from src.core.advisor_cockpit.action_builder import build_source_backed_action
from src.core.advisor_cockpit.action_execution import (
    build_execution_handoff_ready_action,
    build_execution_status_attention_action,
)
from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
    HouseViewImpactActionSource,
    MeetingPreparationActionSource,
    MemoPackageBlockedActionSource,
    PolicyReviewActionSource,
    ReportRenderArchiveActionSource,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
)
from src.core.advisor_cockpit.models import (
    AdvisorCockpitActionStatus,
    AdvisoryActionItem,
)
from src.core.advisor_cockpit.vocabulary import sort_cockpit_action_items

LOTUS_ADVISE_SOURCE_SYSTEM = action_components.LOTUS_ADVISE_SOURCE_SYSTEM
_dependency_readiness = action_components.dependency_readiness
_evidence_ref = action_components.evidence_ref
_lineage_refs = action_components.lineage_refs
_source_readiness_gap = action_components.source_readiness_gap
_unique_ordered = action_components.unique_ordered


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
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
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
                _source_readiness_gap(
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
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
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
                _source_readiness_gap(
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
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
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
                _source_readiness_gap(
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


def build_house_view_impact_action(source: HouseViewImpactActionSource) -> AdvisoryActionItem:
    return build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id=source.cohort_id,
            action_family="HOUSE_VIEW_IMPACT_REVIEW",
            status="PENDING_REVIEW",
            priority="MEDIUM",
            owner_role="PORTFOLIO_MANAGER",
            title="Tactical house-view impact review",
            next_required_action=(
                "Review the source-backed tactical house-view cohort before discretionary "
                "portfolio-management actioning."
            ),
            reason_codes=[source.impact_code, "TACTICAL_HOUSE_VIEW_REVIEW_REQUIRED"],
            source_refs=CockpitActionSourceRefs(portfolio_id=source.portfolio_id),
            due_at=source.due_at,
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
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
            sla_age_band=action_components.initial_sla_age_band(source.due_at),
            materiality_rank=source.materiality_rank,
            source_timestamp=source.source_timestamp,
            dependency_readiness=[
                _dependency_readiness(
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
