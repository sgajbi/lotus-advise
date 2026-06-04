from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.action_factory import build_source_backed_cockpit_actions
from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
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
from src.core.advisor_cockpit.source_projection import (
    ACTIVE_PROPOSAL_STATES,
    APPROVAL_DEPENDENCY_STATES,
    COCKPIT_POLICY_REVIEW_STATUSES,
    FOLLOW_UP_PROPOSAL_STATES,
    approvals_by_proposal,
    build_approval_dependency_sources,
    build_client_follow_up_sources,
    build_execution_handoff_sources,
    build_execution_status_sources,
    build_meeting_preparation_sources,
    build_memo_block_sources,
    build_policy_review_sources,
    build_report_render_archive_sources,
    events_by_proposal,
    proposal_by_id,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)

COCKPIT_SOURCE_BATCH_MAX_ITEMS = 100

__all__ = [
    "ACTIVE_PROPOSAL_STATES",
    "APPROVAL_DEPENDENCY_STATES",
    "AdvisorCockpitSourceBatch",
    "AdvisorCockpitSourceReadModel",
    "COCKPIT_POLICY_REVIEW_STATUSES",
    "COCKPIT_SOURCE_BATCH_MAX_ITEMS",
    "FOLLOW_UP_PROPOSAL_STATES",
    "build_advisor_cockpit_source_read_model",
]


class AdvisorCockpitSourceBatch(BaseModel):
    proposals: list[ProposalRecord] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded proposal records in the bounded cockpit scope.",
    )
    policy_evaluations: list[PolicyEvaluationRecord] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded policy evaluation records in the bounded cockpit scope.",
    )
    memos: list[ProposalMemoRecord] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded proposal memo records in the bounded cockpit scope.",
    )
    approvals: list[ProposalApprovalRecordData] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded proposal approval records in the bounded cockpit scope.",
    )
    workflow_events: list[ProposalWorkflowEventRecord] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded proposal workflow events in the bounded cockpit scope.",
    )
    house_view_impacts: list[HouseViewImpactActionSource] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Source-backed tactical house-view impacts supplied by the source authority.",
    )
    supportability_events: list[SupportabilityDegradedActionSource] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Preloaded source dependency readiness events.",
    )
    unsupported_capabilities: list[UnsupportedCapabilityActionSource] = Field(
        default_factory=list,
        max_length=COCKPIT_SOURCE_BATCH_MAX_ITEMS,
        description="Explicit unsupported capability markers for the bounded scope.",
    )


class AdvisorCockpitSourceReadModel(BaseModel):
    source_counts: dict[str, int] = Field(
        description="Counts of preloaded source records consumed by the read model."
    )
    policy_reviews: list[PolicyReviewActionSource] = Field(
        description="Policy evaluation sources requiring cockpit action."
    )
    memo_blocks: list[MemoPackageBlockedActionSource] = Field(
        description="Memo sources requiring blocked package attention."
    )
    meeting_preparations: list[MeetingPreparationActionSource] = Field(
        description="Meeting-preparation sources for active advisory proposals."
    )
    client_follow_ups: list[ClientFollowUpActionSource] = Field(
        description="Advisor-owned follow-up requirements from proposal lifecycle posture."
    )
    approval_dependencies: list[ApprovalDependencyActionSource] = Field(
        description="Proposal approval and consent dependencies requiring queue attention."
    )
    report_render_archive_items: list[ReportRenderArchiveActionSource] = Field(
        description="Report/render/archive readiness sources requiring owner attention."
    )
    execution_handoffs: list[ExecutionHandoffReadyActionSource] = Field(
        description="Execution handoff readiness sources."
    )
    execution_status_items: list[ExecutionStatusAttentionActionSource] = Field(
        description="Execution status attention sources."
    )
    house_view_impacts: list[HouseViewImpactActionSource] = Field(
        description="Source-backed tactical house-view impact sources."
    )
    supportability_events: list[SupportabilityDegradedActionSource] = Field(
        description="Source dependency readiness events."
    )
    unsupported_capabilities: list[UnsupportedCapabilityActionSource] = Field(
        description="Unsupported capability markers that must remain visible."
    )
    action_items: list[AdvisoryActionItem] = Field(
        description=(
            "Sorted source-backed cockpit action items derived from the bounded source batch."
        )
    )


def build_advisor_cockpit_source_read_model(
    batch: AdvisorCockpitSourceBatch,
) -> AdvisorCockpitSourceReadModel:
    proposals_by_id = proposal_by_id(batch.proposals)
    approvals_by_proposal_id = approvals_by_proposal(batch.approvals)
    events_by_proposal_id = events_by_proposal(batch.workflow_events)
    policy_reviews = build_policy_review_sources(batch.policy_evaluations)
    memo_blocks = build_memo_block_sources(records=batch.memos, proposals=proposals_by_id)
    meeting_preparations = build_meeting_preparation_sources(batch.proposals)
    client_follow_ups = build_client_follow_up_sources(batch.proposals)
    approval_dependencies = build_approval_dependency_sources(
        records=batch.proposals,
        approvals=approvals_by_proposal_id,
    )
    report_render_archive_items = build_report_render_archive_sources(
        records=batch.memos,
        proposals=proposals_by_id,
    )
    execution_handoffs = build_execution_handoff_sources(
        records=batch.proposals,
        events=events_by_proposal_id,
    )
    execution_status_items = build_execution_status_sources(
        proposals=proposals_by_id,
        events=events_by_proposal_id,
    )
    action_items = build_source_backed_cockpit_actions(
        policy_reviews=policy_reviews,
        memo_blocks=memo_blocks,
        meeting_preparations=meeting_preparations,
        client_follow_ups=client_follow_ups,
        approval_dependencies=approval_dependencies,
        report_render_archive_items=report_render_archive_items,
        execution_handoffs=execution_handoffs,
        execution_status_items=execution_status_items,
        house_view_impacts=batch.house_view_impacts,
        supportability_events=batch.supportability_events,
        unsupported_capabilities=batch.unsupported_capabilities,
    )
    return AdvisorCockpitSourceReadModel(
        source_counts={
            "proposals": len(batch.proposals),
            "policy_evaluations": len(batch.policy_evaluations),
            "memos": len(batch.memos),
            "approvals": len(batch.approvals),
            "workflow_events": len(batch.workflow_events),
            "house_view_impacts": len(batch.house_view_impacts),
            "supportability_events": len(batch.supportability_events),
            "unsupported_capabilities": len(batch.unsupported_capabilities),
        },
        policy_reviews=policy_reviews,
        memo_blocks=memo_blocks,
        meeting_preparations=meeting_preparations,
        client_follow_ups=client_follow_ups,
        approval_dependencies=approval_dependencies,
        report_render_archive_items=report_render_archive_items,
        execution_handoffs=execution_handoffs,
        execution_status_items=execution_status_items,
        house_view_impacts=list(batch.house_view_impacts),
        supportability_events=list(batch.supportability_events),
        unsupported_capabilities=list(batch.unsupported_capabilities),
        action_items=action_items,
    )
