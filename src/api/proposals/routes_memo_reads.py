from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import ProposalIdPath
from src.api.proposals.memo_parameters import (
    ProposalMemoAudienceQuery,
    ProposalMemoSourceVersionNoPath,
)
from src.api.proposals.memo_responses import (
    MEMO_LINEAGE_RESPONSES,
    MEMO_READ_RESPONSES,
)
from src.core.proposals import (
    ProposalMemoLineageResponse,
    ProposalMemoProjectionResponse,
    ProposalMemoReplayEvidenceResponse,
    ProposalMemoResponse,
)
from src.core.proposals.memo_api import (
    get_memo_lineage_response,
    get_memo_projection_response,
    get_memo_replay_evidence_response,
    get_memo_response,
)
from src.core.proposals.repository import ProposalRepository


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo",
    response_model=ProposalMemoResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Read Proposal Memo",
    description=(
        "Returns the exact persisted memo evidence pack, projection policy, append-only memo "
        "audit events, and replay links for an immutable proposal version."
    ),
    responses=MEMO_READ_RESPONSES,
)
def get_proposal_memo(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
) -> ProposalMemoResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: get_memo_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/projection",
    response_model=ProposalMemoProjectionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Read Proposal Memo Projection",
    description=(
        "Returns memo projection policy and audience-filtered sections from the persisted memo. "
        "Projection is read-only and keeps client-ready publication blocked in Slice 7."
    ),
    responses=MEMO_READ_RESPONSES,
)
def get_proposal_memo_projection(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
    audience: ProposalMemoAudienceQuery = None,
) -> ProposalMemoProjectionResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: get_memo_projection_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            audience=audience,
        )
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/memos/lineage",
    response_model=ProposalMemoLineageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Get Proposal Memo Lineage",
    description=(
        "Returns persisted memo lineage for a proposal, including memo hashes, source hashes, "
        "lifecycle status, and event counts."
    ),
    responses=MEMO_LINEAGE_RESPONSES,
)
def get_proposal_memo_lineage(
    proposal_id: ProposalIdPath,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
) -> ProposalMemoLineageResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: get_memo_lineage_response(repository=repository, proposal_id=proposal_id)
    )


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/replay-evidence",
    response_model=ProposalMemoReplayEvidenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Get Proposal Memo Replay Evidence",
    description=(
        "Returns memo replay evidence with proposal source hashes, memo hashes, replay metadata, "
        "projection posture, and append-only memo audit events."
    ),
    responses=MEMO_READ_RESPONSES,
)
def get_proposal_memo_replay_evidence(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
) -> ProposalMemoReplayEvidenceResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: get_memo_replay_evidence_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
    )


__all__ = [
    "get_proposal_memo",
    "get_proposal_memo_lineage",
    "get_proposal_memo_projection",
    "get_proposal_memo_replay_evidence",
]
