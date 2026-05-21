from dataclasses import dataclass

from src.core.proposals.models import ProposalRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalCommandReadModel:
    proposal: ProposalRecord | None


def load_proposal_command_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalCommandReadModel:
    return ProposalCommandReadModel(
        proposal=repository.get_proposal(proposal_id=proposal_id),
    )
