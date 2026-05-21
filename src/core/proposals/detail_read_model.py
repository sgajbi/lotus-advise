from dataclasses import dataclass

from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalDetailReadModel:
    proposal: ProposalRecord | None
    current_version: ProposalVersionRecord | None


def load_proposal_detail_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalDetailReadModel:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        return ProposalDetailReadModel(proposal=None, current_version=None)

    return ProposalDetailReadModel(
        proposal=proposal,
        current_version=repository.get_current_version(proposal_id=proposal_id),
    )
