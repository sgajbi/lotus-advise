from src.core.advisor_cockpit.action_sources import (
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
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
from src.core.advisor_cockpit.source_projection_proposal import (
    ACTIVE_PROPOSAL_STATES as ACTIVE_PROPOSAL_STATES,
)
from src.core.advisor_cockpit.source_projection_proposal import (
    APPROVAL_DEPENDENCY_STATES as APPROVAL_DEPENDENCY_STATES,
)
from src.core.advisor_cockpit.source_projection_proposal import (
    FOLLOW_UP_PROPOSAL_STATES as FOLLOW_UP_PROPOSAL_STATES,
)
from src.core.advisor_cockpit.source_projection_proposal import (
    build_approval_dependency_sources as build_approval_dependency_sources,
)
from src.core.advisor_cockpit.source_projection_proposal import (
    build_client_follow_up_sources as build_client_follow_up_sources,
)
from src.core.advisor_cockpit.source_projection_proposal import (
    build_meeting_preparation_sources as build_meeting_preparation_sources,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.workflow_rules import execution_status_for_event


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
