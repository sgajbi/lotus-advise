from dataclasses import dataclass

from src.core.proposals.models import (
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalVersionReplayReferents:
    proposal: ProposalRecord | None
    version: ProposalVersionRecord | None
    events: list[ProposalWorkflowEventRecord]


def load_proposal_version_replay_referents(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalVersionReplayReferents:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        return ProposalVersionReplayReferents(proposal=None, version=None, events=[])

    version = repository.get_version(proposal_id=proposal_id, version_no=version_no)
    if version is None:
        return ProposalVersionReplayReferents(proposal=proposal, version=None, events=[])

    events = repository.list_events(proposal_id=proposal_id)
    return ProposalVersionReplayReferents(proposal=proposal, version=version, events=events)
