from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
    MeetingPreparationActionSource,
    ReportRenderArchiveActionSource,
)
from src.core.advisor_cockpit.source_projection_policy_memo import (
    COCKPIT_POLICY_REVIEW_STATUSES as COCKPIT_POLICY_REVIEW_STATUSES,
)
from src.core.advisor_cockpit.source_projection_policy_memo import (
    build_memo_block_sources as build_memo_block_sources,
)
from src.core.advisor_cockpit.source_projection_policy_memo import (
    build_policy_review_sources as build_policy_review_sources,
)
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
FOLLOW_UP_PROPOSAL_STATES = frozenset({"AWAITING_CLIENT_CONSENT"})
APPROVAL_DEPENDENCY_STATES: dict[str, ProposalApprovalType] = {
    "RISK_REVIEW": "RISK",
    "COMPLIANCE_REVIEW": "COMPLIANCE",
    "AWAITING_CLIENT_CONSENT": "CLIENT_CONSENT",
}


def proposal_by_id(proposals: list[ProposalRecord]) -> dict[str, ProposalRecord]:
    return {proposal.proposal_id: proposal for proposal in proposals}


def approvals_by_proposal(
    approvals: list[ProposalApprovalRecordData],
) -> dict[str, list[ProposalApprovalRecordData]]:
    grouped: dict[str, list[ProposalApprovalRecordData]] = {}
    for approval in approvals:
        grouped.setdefault(approval.proposal_id, []).append(approval)
    return grouped


def events_by_proposal(
    events: list[ProposalWorkflowEventRecord],
) -> dict[str, list[ProposalWorkflowEventRecord]]:
    grouped: dict[str, list[ProposalWorkflowEventRecord]] = {}
    for event in events:
        grouped.setdefault(event.proposal_id, []).append(event)
    return grouped


def build_meeting_preparation_sources(
    records: list[ProposalRecord],
) -> list[MeetingPreparationActionSource]:
    return [
        _meeting_preparation_source(record)
        for record in records
        if record.current_state in ACTIVE_PROPOSAL_STATES
    ]


def build_client_follow_up_sources(
    records: list[ProposalRecord],
) -> list[ClientFollowUpActionSource]:
    return [
        _client_follow_up_source(record)
        for record in records
        if record.current_state in FOLLOW_UP_PROPOSAL_STATES
    ]


def build_approval_dependency_sources(
    *,
    records: list[ProposalRecord],
    approvals: dict[str, list[ProposalApprovalRecordData]],
) -> list[ApprovalDependencyActionSource]:
    return [
        source
        for record in records
        if (
            source := _approval_dependency_source(
                proposal=record,
                approvals=approvals.get(record.proposal_id, []),
            )
        )
        is not None
    ]


def build_report_render_archive_sources(
    *,
    records: list[ProposalMemoRecord],
    proposals: dict[str, ProposalRecord],
) -> list[ReportRenderArchiveActionSource]:
    return [
        source
        for record in records
        if (
            source := _report_readiness_source(
                record,
                proposal=proposals.get(record.proposal_id),
            )
        )
        is not None
    ]


def build_execution_handoff_sources(
    *,
    records: list[ProposalRecord],
    events: dict[str, list[ProposalWorkflowEventRecord]],
) -> list[ExecutionHandoffReadyActionSource]:
    return [
        source
        for record in records
        if (
            source := _execution_handoff_source(
                proposal=record,
                events=events.get(record.proposal_id, []),
            )
        )
        is not None
    ]


def build_execution_status_sources(
    *,
    proposals: dict[str, ProposalRecord],
    events: dict[str, list[ProposalWorkflowEventRecord]],
) -> list[ExecutionStatusAttentionActionSource]:
    return [
        source
        for proposal_id, proposal_events in events.items()
        if (
            source := _execution_status_source(
                proposal=proposals.get(proposal_id),
                events=proposal_events,
            )
        )
        is not None
    ]


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
