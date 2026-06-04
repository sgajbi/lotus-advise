from src.core.advisor_cockpit.source_projection_execution import (
    build_execution_handoff_sources as build_execution_handoff_sources,
)
from src.core.advisor_cockpit.source_projection_execution import (
    build_execution_status_sources as build_execution_status_sources,
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
from src.core.advisor_cockpit.source_projection_reporting import (
    build_report_render_archive_sources as build_report_render_archive_sources,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)


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
