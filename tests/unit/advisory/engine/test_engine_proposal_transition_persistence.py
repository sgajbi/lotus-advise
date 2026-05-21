from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.transition_persistence import (
    persist_proposal_approval_transition,
    persist_proposal_transition,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 21, 0, tzinfo=timezone.utc)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_transition_persist",
        portfolio_id="pf_transition_persist",
        mandate_id="mandate_transition_persist",
        jurisdiction="SG",
        created_by="advisor_transition_persist",
        created_at=_now(),
        last_event_at=_now(),
        current_state="DRAFT",
        current_version_no=1,
        title="Transition persistence proposal",
    )


def _event(
    *,
    event_id: str = "pwe_transition_persist",
    event_type: str = "SUBMITTED_FOR_RISK_REVIEW",
    to_state: str = "RISK_REVIEW",
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id="pp_transition_persist",
        event_type=event_type,
        from_state="DRAFT",
        to_state=to_state,
        actor_id="advisor_transition_persist",
        occurred_at=_now(),
        reason_json={},
        related_version_no=1,
    )


def _approval() -> ProposalApprovalRecordData:
    return ProposalApprovalRecordData(
        approval_id="pap_transition_persist",
        proposal_id="pp_transition_persist",
        approval_type="RISK",
        approved=True,
        actor_id="risk_approver",
        occurred_at=_now(),
        details_json={"note": "approved"},
        related_version_no=1,
    )


def test_persist_proposal_transition_updates_aggregate_and_event():
    repository = InMemoryProposalRepository()
    proposal = _proposal()
    repository.create_proposal(proposal)
    event = _event()
    proposal.current_state = "RISK_REVIEW"
    proposal.last_event_at = event.occurred_at

    result = persist_proposal_transition(
        repository=repository,
        proposal=proposal,
        event=event,
    )

    assert result.proposal.current_state == "RISK_REVIEW"
    assert result.event.event_id == "pwe_transition_persist"
    stored = repository.get_proposal(proposal_id="pp_transition_persist")
    assert stored is not None
    assert stored.current_state == "RISK_REVIEW"
    assert repository.list_events(proposal_id="pp_transition_persist")[0].event_id == (
        "pwe_transition_persist"
    )


def test_persist_proposal_approval_transition_stores_approval_referent():
    repository = InMemoryProposalRepository()
    proposal = _proposal()
    repository.create_proposal(proposal)
    event = _event(
        event_id="pwe_transition_approval",
        event_type="RISK_APPROVED",
        to_state="COMPLIANCE_REVIEW",
    )
    approval = _approval()
    proposal.current_state = "COMPLIANCE_REVIEW"
    proposal.last_event_at = event.occurred_at

    result = persist_proposal_approval_transition(
        repository=repository,
        proposal=proposal,
        event=event,
        approval=approval,
    )

    assert result.proposal.current_state == "COMPLIANCE_REVIEW"
    assert result.approval is not None
    assert result.approval.approval_id == "pap_transition_persist"
    approvals = repository.list_approvals(proposal_id="pp_transition_persist")
    assert approvals[0].approval_id == "pap_transition_persist"
