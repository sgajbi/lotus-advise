from datetime import datetime, timezone

from src.core.proposals.list_read_model import load_proposal_list_read_model
from src.core.proposals.models import ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 18, 0, tzinfo=timezone.utc)


def _proposal(
    proposal_id: str,
    *,
    portfolio_id: str = "pf_list",
    state: str = "DRAFT",
    created_by: str = "advisor_list",
) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id=portfolio_id,
        mandate_id="mandate_list",
        jurisdiction="SG",
        created_by=created_by,
        created_at=_now(),
        last_event_at=_now(),
        current_state=state,
        current_version_no=1,
        title=f"List read model {proposal_id}",
    )


def test_load_proposal_list_read_model_preserves_filters_and_paging():
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal("pp_list_a"))
    repository.create_proposal(_proposal("pp_list_b", state="EXECUTION_READY"))
    repository.create_proposal(_proposal("pp_list_c", portfolio_id="pf_other"))

    read_model = load_proposal_list_read_model(
        repository=repository,
        portfolio_id="pf_list",
        state=None,
        created_by="advisor_list",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=None,
    )

    assert [proposal.proposal_id for proposal in read_model.proposals] == ["pp_list_b"]
    assert read_model.next_cursor == "pp_list_b"

    next_page = load_proposal_list_read_model(
        repository=repository,
        portfolio_id="pf_list",
        state=None,
        created_by="advisor_list",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=read_model.next_cursor,
    )

    assert [proposal.proposal_id for proposal in next_page.proposals] == ["pp_list_a"]
    assert next_page.next_cursor is None


def test_load_proposal_list_read_model_preserves_empty_result_boundary():
    read_model = load_proposal_list_read_model(
        repository=InMemoryProposalRepository(),
        portfolio_id="pf_missing",
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=25,
        cursor=None,
    )

    assert read_model.proposals == []
    assert read_model.next_cursor is None
