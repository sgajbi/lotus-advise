from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar, cast

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
from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.action_policy import build_policy_review_required_action
from src.core.advisor_cockpit.action_reporting import (
    build_memo_package_blocked_action,
    build_report_render_archive_action,
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
from src.core.advisor_cockpit.vocabulary import sort_cockpit_action_items

_ActionSourceT = TypeVar("_ActionSourceT")

LOTUS_ADVISE_SOURCE_SYSTEM = action_components.LOTUS_ADVISE_SOURCE_SYSTEM
_dependency_readiness = action_components.dependency_readiness
_evidence_ref = action_components.evidence_ref
_lineage_refs = action_components.lineage_refs
_unique_ordered = action_components.unique_ordered


def _append_source_actions(
    actions: list[AdvisoryActionItem],
    sources: Sequence[_ActionSourceT],
    builder: Callable[[_ActionSourceT], AdvisoryActionItem],
) -> None:
    actions.extend(builder(source) for source in sources)


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
    actions: list[AdvisoryActionItem] = []
    _append_source_actions(actions, policy_reviews, build_policy_review_required_action)
    _append_source_actions(actions, memo_blocks, build_memo_package_blocked_action)
    _append_source_actions(actions, meeting_preparations, build_meeting_preparation_action)
    _append_source_actions(actions, client_follow_ups, build_client_follow_up_action)
    _append_source_actions(actions, approval_dependencies, build_approval_dependency_action)
    _append_source_actions(
        actions,
        report_render_archive_items,
        build_report_render_archive_action,
    )
    _append_source_actions(actions, execution_handoffs, build_execution_handoff_ready_action)
    _append_source_actions(
        actions,
        execution_status_items,
        build_execution_status_attention_action,
    )
    _append_source_actions(actions, house_view_impacts, build_house_view_impact_action)
    _append_source_actions(actions, supportability_events, build_supportability_degraded_action)
    _append_source_actions(actions, unsupported_capabilities, build_unsupported_capability_action)
    return cast(list[AdvisoryActionItem], sort_cockpit_action_items(actions))
