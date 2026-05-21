from datetime import datetime, timezone

from src.core.proposals.command_read_model import load_proposal_command_read_model
from src.core.proposals.models import ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _proposal() -> ProposalRecord:
    now = datetime(2026, 5, 21, 19, 0, tzinfo=timezone.utc)
    return ProposalRecord(
        proposal_id="pp_command_read",
        portfolio_id="pf_command_read",
        mandate_id="mandate_command_read",
        jurisdiction="SG",
        created_by="advisor_command_read",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="Command read model proposal",
    )


def test_load_proposal_command_read_model_returns_proposal_aggregate():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())

    read_model = load_proposal_command_read_model(
        repository=repository,
        proposal_id="pp_command_read",
    )

    assert read_model.proposal is not None
    assert read_model.proposal.portfolio_id == "pf_command_read"
    assert read_model.proposal.current_state == "DRAFT"


def test_load_proposal_command_read_model_preserves_missing_proposal_boundary():
    read_model = load_proposal_command_read_model(
        repository=InMemoryProposalRepository(),
        proposal_id="pp_missing",
    )

    assert read_model.proposal is None
