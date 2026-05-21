from dataclasses import dataclass

from src.core.proposals.models import ProposalRecord, ProposalWorkflowEventRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalActivityReadModel:
    proposal: ProposalRecord | None
    events: list[ProposalWorkflowEventRecord]


def load_proposal_activity_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalActivityReadModel:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        return ProposalActivityReadModel(proposal=None, events=[])

    return ProposalActivityReadModel(
        proposal=proposal,
        events=repository.list_events(proposal_id=proposal_id),
    )
