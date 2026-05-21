from dataclasses import dataclass

from src.core.proposals.models import ProposalVersionRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalVersionReadModel:
    version: ProposalVersionRecord | None


def load_proposal_version_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalVersionReadModel:
    return ProposalVersionReadModel(
        version=repository.get_version(proposal_id=proposal_id, version_no=version_no),
    )
