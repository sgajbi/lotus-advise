from src.core.advisor_cockpit.action_sources import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
    MeetingPreparationActionSource,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalType,
    ProposalRecord,
)

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
    matching_approvals = _matching_approval_records(
        approvals=approvals,
        approval_type=approval_type,
    )
    if _has_completed_approval(matching_approvals):
        return None
    return _pending_approval_dependency_source(
        proposal=proposal,
        approval_type=approval_type,
        latest_rejection=_latest_rejected_approval(matching_approvals),
    )


def _matching_approval_records(
    *,
    approvals: list[ProposalApprovalRecordData],
    approval_type: ProposalApprovalType,
) -> list[ProposalApprovalRecordData]:
    return [approval for approval in approvals if approval.approval_type == approval_type]


def _has_completed_approval(approvals: list[ProposalApprovalRecordData]) -> bool:
    return any(approval.approved for approval in approvals)


def _pending_approval_dependency_source(
    *,
    proposal: ProposalRecord,
    approval_type: ProposalApprovalType,
    latest_rejection: ProposalApprovalRecordData | None,
) -> ApprovalDependencyActionSource:
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


__all__ = [
    "ACTIVE_PROPOSAL_STATES",
    "APPROVAL_DEPENDENCY_STATES",
    "FOLLOW_UP_PROPOSAL_STATES",
    "build_approval_dependency_sources",
    "build_client_follow_up_sources",
    "build_meeting_preparation_sources",
]
