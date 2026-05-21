from datetime import datetime, timezone

from src.core.proposals.activity_read_model import load_proposal_activity_read_model
from src.core.proposals.models import ProposalRecord, ProposalWorkflowEventRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 11, 0, tzinfo=timezone.utc)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="pp_activity",
        portfolio_id="pf_activity",
        mandate_id="mandate_activity",
        jurisdiction="SG",
        created_by="advisor_activity",
        created_at=_now(),
        last_event_at=_now(),
        current_state="EXECUTION_READY",
        current_version_no=1,
        title="Activity read model proposal",
    )


def _event(event_id: str, event_type: str) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id="pp_activity",
        event_type=event_type,
        from_state="DRAFT",
        to_state="EXECUTION_READY",
        actor_id="advisor_activity",
        occurred_at=_now(),
        reason_json={},
        related_version_no=1,
    )


def test_load_proposal_activity_read_model_returns_proposal_and_ordered_events():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.append_event(_event("pwe_activity_1", "CREATED"))
    repository.append_event(_event("pwe_activity_2", "EXECUTION_REQUESTED"))

    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id="pp_activity",
    )

    assert activity.proposal is not None
    assert activity.proposal.proposal_id == "pp_activity"
    assert [event.event_id for event in activity.events] == [
        "pwe_activity_1",
        "pwe_activity_2",
    ]


def test_load_proposal_activity_read_model_preserves_missing_proposal_boundary():
    activity = load_proposal_activity_read_model(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
    )

    assert activity.proposal is None
    assert activity.events == []
