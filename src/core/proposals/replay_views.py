from __future__ import annotations

from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.models import ProposalCreateResponse
from src.core.proposals.projections import build_create_response_from_referents
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.core.proposals.repository import ProposalRepository
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import build_proposal_version_replay_response


def build_create_response_from_replay_referents(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalCreateResponse:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    response = build_create_response_from_referents(
        proposal=referents.proposal,
        version=referents.version,
        events=referents.events,
    )
    if response is None:
        raise ProposalNotFoundError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
    return response


def build_proposal_version_replay_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> AdvisoryReplayEvidenceResponse:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return build_proposal_version_replay_response(
        proposal=referents.proposal,
        version=referents.version,
        events=referents.events,
    )


__all__ = [
    "build_create_response_from_replay_referents",
    "build_proposal_version_replay_view",
]
