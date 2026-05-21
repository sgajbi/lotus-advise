from dataclasses import dataclass

from src.core.proposals.models import ProposalRecord, ProposalVersionRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalLineageReadModel:
    proposal: ProposalRecord | None
    versions_by_number: dict[int, ProposalVersionRecord | None]


def load_proposal_lineage_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalLineageReadModel:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        return ProposalLineageReadModel(proposal=None, versions_by_number={})

    return ProposalLineageReadModel(
        proposal=proposal,
        versions_by_number={
            version.version_no: version
            for version in repository.list_versions(proposal_id=proposal_id)
        },
    )
