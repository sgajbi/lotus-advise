from __future__ import annotations

from pydantic import BaseModel, Field

from src.core.advisor_cockpit.action_factory import (
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
    build_source_backed_cockpit_actions,
)
from src.core.advisor_cockpit.models import AdvisoryActionItem
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalType,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.workflow_rules import execution_status_for_event

ACTIVE_PROPOSAL_STATES = frozenset(
    {
        "DRAFT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "AWAITING_CLIENT_CONSENT",
        "EXECUTION_READY",
    }
)
COCKPIT_POLICY_REVIEW_STATUSES = frozenset({"PENDING_REVIEW", "BLOCKED"})
FOLLOW_UP_PROPOSAL_STATES = frozenset({"AWAITING_CLIENT_CONSENT"})
APPROVAL_DEPENDENCY_STATES: dict[str, ProposalApprovalType] = {
    "RISK_REVIEW": "RISK",
    "COMPLIANCE_REVIEW": "COMPLIANCE",
    "AWAITING_CLIENT_CONSENT": "CLIENT_CONSENT",
}


class AdvisorCockpitSourceBatch(BaseModel):
    proposals: list[ProposalRecord] = Field(
        default_factory=list,
        description="Preloaded proposal records in the bounded cockpit scope.",
    )
    policy_evaluations: list[PolicyEvaluationRecord] = Field(
        default_factory=list,
        description="Preloaded policy evaluation records in the bounded cockpit scope.",
    )
    memos: list[ProposalMemoRecord] = Field(
        default_factory=list,
        description="Preloaded proposal memo records in the bounded cockpit scope.",
    )
    approvals: list[ProposalApprovalRecordData] = Field(
        default_factory=list,
        description="Preloaded proposal approval records in the bounded cockpit scope.",
    )
    workflow_events: list[ProposalWorkflowEventRecord] = Field(
        default_factory=list,
        description="Preloaded proposal workflow events in the bounded cockpit scope.",
    )
    house_view_impacts: list[HouseViewImpactActionSource] = Field(
        default_factory=list,
        description="Source-backed tactical house-view impacts supplied by the source authority.",
    )
    supportability_events: list[SupportabilityDegradedActionSource] = Field(
        default_factory=list,
        description="Preloaded source dependency readiness events.",
    )
    unsupported_capabilities: list[UnsupportedCapabilityActionSource] = Field(
        default_factory=list,
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
    proposals_by_id = _proposal_by_id(batch.proposals)
    approvals_by_proposal = _approvals_by_proposal(batch.approvals)
    events_by_proposal = _events_by_proposal(batch.workflow_events)
    policy_reviews = [
        _policy_review_source(record)
        for record in batch.policy_evaluations
        if record.evaluation_status in COCKPIT_POLICY_REVIEW_STATUSES
    ]
    memo_blocks = [
        source
        for record in batch.memos
        if (
            source := _memo_block_source(
                record,
                proposal=proposals_by_id.get(record.proposal_id),
            )
        )
        is not None
    ]
    meeting_preparations = [
        _meeting_preparation_source(record)
        for record in batch.proposals
        if record.current_state in ACTIVE_PROPOSAL_STATES
    ]
    client_follow_ups = [
        _client_follow_up_source(record)
        for record in batch.proposals
        if record.current_state in FOLLOW_UP_PROPOSAL_STATES
    ]
    approval_dependencies = [
        source
        for record in batch.proposals
        if (
            source := _approval_dependency_source(
                proposal=record,
                approvals=approvals_by_proposal.get(record.proposal_id, []),
            )
        )
        is not None
    ]
    report_render_archive_items = [
        source
        for record in batch.memos
        if (
            source := _report_readiness_source(
                record,
                proposal=proposals_by_id.get(record.proposal_id),
            )
        )
        is not None
    ]
    execution_handoffs = [
        source
        for record in batch.proposals
        if (
            source := _execution_handoff_source(
                proposal=record,
                events=events_by_proposal.get(record.proposal_id, []),
            )
        )
        is not None
    ]
    execution_status_items = [
        source
        for proposal_id, events in events_by_proposal.items()
        if (
            source := _execution_status_source(
                proposal=proposals_by_id.get(proposal_id),
                events=events,
            )
        )
        is not None
    ]
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


def _policy_review_source(record: PolicyEvaluationRecord) -> PolicyReviewActionSource:
    return PolicyReviewActionSource(
        policy_evaluation_id=record.evaluation_id,
        portfolio_id=record.portfolio_id,
        proposal_id=record.proposal_id,
        policy_result=record.evaluation_status,
        summary="Policy evaluation requires review before client-ready posture can change.",
        source_timestamp=record.generated_at,
        materiality_rank=90 if record.evaluation_status == "BLOCKED" else 80,
        lineage_id=f"policy_evaluation:{record.evaluation_id}",
        content_hash=record.evaluation_hash,
    )


def _memo_block_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> MemoPackageBlockedActionSource | None:
    blockage_code = _memo_blockage_code(record)
    if blockage_code is None:
        return None
    return MemoPackageBlockedActionSource(
        memo_id=record.memo_id,
        proposal_id=record.proposal_id,
        portfolio_id=proposal.portfolio_id if proposal is not None else None,
        blockage_code=blockage_code,
        summary="Proposal memo package is not ready for advisor-use packaging.",
        owner_role="REPORTING_OWNER",
        source_timestamp=record.created_at.isoformat(),
        materiality_rank=70 if record.memo_status == "BLOCKED" else 60,
        lineage_id=f"proposal_memo:{record.memo_id}",
        content_hash=record.memo_hash,
    )


def _meeting_preparation_source(record: ProposalRecord) -> MeetingPreparationActionSource:
    return MeetingPreparationActionSource(
        preparation_id=f"prep_{record.proposal_id}_v{record.current_version_no}",
        context_ref=record.proposal_id,
        context_type="PROPOSAL",
        portfolio_id=record.portfolio_id,
        proposal_id=record.proposal_id,
        summary="Active advisory proposal is available for meeting preparation.",
        source_timestamp=record.last_event_at.isoformat(),
        materiality_rank=50 if record.current_state == "EXECUTION_READY" else 30,
    )


def _client_follow_up_source(record: ProposalRecord) -> ClientFollowUpActionSource:
    return ClientFollowUpActionSource(
        follow_up_id=f"follow_up_{record.proposal_id}_client_consent",
        proposal_id=record.proposal_id,
        portfolio_id=record.portfolio_id,
        follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
        summary=(
            "Proposal is awaiting client consent; advisor follow-up is required before "
            "execution readiness can change, while external client communication remains gated."
        ),
        source_timestamp=record.last_event_at.isoformat(),
        materiality_rank=65,
    )


def _approval_dependency_source(
    *,
    proposal: ProposalRecord,
    approvals: list[ProposalApprovalRecordData],
) -> ApprovalDependencyActionSource | None:
    approval_type = APPROVAL_DEPENDENCY_STATES.get(proposal.current_state)
    if approval_type is None:
        return None
    matching_approvals = [
        approval for approval in approvals if approval.approval_type == approval_type
    ]
    if any(approval.approved for approval in matching_approvals):
        return None
    latest_rejection = _latest_rejected_approval(matching_approvals)
    approval_status = "REJECTED" if latest_rejection is not None else "PENDING"
    dependency_id = f"approval_dependency_{proposal.proposal_id}_{approval_type.lower()}"
    return ApprovalDependencyActionSource(
        dependency_id=dependency_id,
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        approval_type=approval_type,
        approval_status=approval_status,
        summary=_approval_dependency_summary(
            proposal_state=proposal.current_state,
            approval_type=approval_type,
            approval_status=approval_status,
        ),
        source_timestamp=(
            latest_rejection.occurred_at.isoformat()
            if latest_rejection is not None
            else proposal.last_event_at.isoformat()
        ),
        materiality_rank=75 if approval_type != "CLIENT_CONSENT" else 68,
    )


def _approvals_by_proposal(
    approvals: list[ProposalApprovalRecordData],
) -> dict[str, list[ProposalApprovalRecordData]]:
    grouped: dict[str, list[ProposalApprovalRecordData]] = {}
    for approval in approvals:
        grouped.setdefault(approval.proposal_id, []).append(approval)
    return grouped


def _latest_rejected_approval(
    approvals: list[ProposalApprovalRecordData],
) -> ProposalApprovalRecordData | None:
    rejected = [approval for approval in approvals if not approval.approved]
    if not rejected:
        return None
    return sorted(rejected, key=lambda item: (item.occurred_at, item.approval_id))[-1]


def _approval_dependency_summary(
    *,
    proposal_state: str,
    approval_type: ProposalApprovalType,
    approval_status: str,
) -> str:
    if approval_status == "REJECTED":
        return (
            f"{approval_type} approval was rejected; proposal state {proposal_state} "
            "cannot progress until the source lifecycle is remediated."
        )
    return (
        f"{approval_type} approval is pending for proposal state {proposal_state}; "
        "the cockpit surfaces the queue without granting approval authority."
    )


def _report_readiness_source(
    record: ProposalMemoRecord,
    *,
    proposal: ProposalRecord | None,
) -> ReportRenderArchiveActionSource | None:
    if record.memo_status != "READY":
        return None
    if not record.report_package_events_json:
        return ReportRenderArchiveActionSource(
            readiness_id=f"report_archive_readiness_{record.memo_id}_report_package",
            memo_id=record.memo_id,
            proposal_id=record.proposal_id,
            portfolio_id=proposal.portfolio_id if proposal is not None else None,
            readiness_code="REPORT_PACKAGE_NOT_REQUESTED",
            summary=(
                "Advisor-use memo is ready, but report/render/archive package evidence is not "
                "recorded."
            ),
            owner_role="REPORTING_OWNER",
            source_timestamp=record.created_at.isoformat(),
            materiality_rank=58,
            lineage_id=f"proposal_memo:{record.memo_id}",
            content_hash=record.memo_hash,
        )
    if not record.archive_refs_json:
        return ReportRenderArchiveActionSource(
            readiness_id=f"report_archive_readiness_{record.memo_id}_archive_ref",
            memo_id=record.memo_id,
            proposal_id=record.proposal_id,
            portfolio_id=proposal.portfolio_id if proposal is not None else None,
            readiness_code="ARCHIVE_REF_MISSING",
            summary="Report package event exists, but archive reference evidence is not recorded.",
            owner_role="ARCHIVE_OWNER",
            source_timestamp=record.created_at.isoformat(),
            materiality_rank=54,
            lineage_id=f"proposal_memo:{record.memo_id}",
            content_hash=record.memo_hash,
        )
    return None


def _execution_handoff_source(
    *,
    proposal: ProposalRecord,
    events: list[ProposalWorkflowEventRecord],
) -> ExecutionHandoffReadyActionSource | None:
    if proposal.current_state != "EXECUTION_READY":
        return None
    if any(event.event_type == "EXECUTION_REQUESTED" for event in events):
        return None
    return ExecutionHandoffReadyActionSource(
        handoff_id=f"execution_handoff_ready_{proposal.proposal_id}",
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        source_timestamp=proposal.last_event_at.isoformat(),
        materiality_rank=62,
    )


def _execution_status_source(
    *,
    proposal: ProposalRecord | None,
    events: list[ProposalWorkflowEventRecord],
) -> ExecutionStatusAttentionActionSource | None:
    if proposal is None:
        return None
    latest_event = _latest_execution_event(events)
    if latest_event is None or latest_event.event_type == "EXECUTED":
        return None
    handoff_status = execution_status_for_event(latest_event.event_type)
    if handoff_status == "NOT_REQUESTED":
        return None
    execution_ref = str(
        latest_event.reason_json.get("execution_request_id")
        or latest_event.reason_json.get("external_execution_id")
        or latest_event.event_id
    )
    return ExecutionStatusAttentionActionSource(
        execution_ref=execution_ref,
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        handoff_status=handoff_status,
        summary=f"Execution handoff status is {handoff_status}; downstream execution remains SOR.",
        source_timestamp=latest_event.occurred_at.isoformat(),
        materiality_rank=72 if handoff_status in {"REJECTED", "CANCELLED", "EXPIRED"} else 50,
    )


def _latest_execution_event(
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowEventRecord | None:
    execution_events = [
        event for event in events if execution_status_for_event(event.event_type) != "NOT_REQUESTED"
    ]
    if not execution_events:
        return None
    return sorted(execution_events, key=lambda item: (item.occurred_at, item.event_id))[-1]


def _events_by_proposal(
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, list[ProposalWorkflowEventRecord]]:
    grouped: dict[str, list[ProposalWorkflowEventRecord]] = {}
    for event in events:
        grouped.setdefault(event.proposal_id, []).append(event)
    return grouped


def _proposal_by_id(proposals: list[ProposalRecord]) -> dict[str, ProposalRecord]:
    return {proposal.proposal_id: proposal for proposal in proposals}


def _memo_blockage_code(record: ProposalMemoRecord) -> str | None:
    if record.memo_status == "BLOCKED":
        return "MEMO_STATUS_BLOCKED"
    if record.lifecycle_status != "FINALIZED":
        return "MEMO_FINALIZATION_REQUIRED"
    if not record.review_events_json:
        return "MEMO_REVIEW_REQUIRED"
    return None
