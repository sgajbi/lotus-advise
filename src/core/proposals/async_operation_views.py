from __future__ import annotations

from src.core.proposals.async_operation_read_model import (
    load_proposal_async_operation_by_correlation_read_model,
    load_proposal_async_operation_read_model,
)
from src.core.proposals.async_replay import load_async_operation_replay_referents
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.models import ProposalAsyncOperationStatusResponse
from src.core.proposals.projections import to_async_status_response
from src.core.proposals.repository import ProposalRepository
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.core.replay.service import build_async_operation_replay_response


def build_async_operation_status_view(
    *,
    repository: ProposalRepository,
    operation_id: str,
) -> ProposalAsyncOperationStatusResponse:
    read_model = load_proposal_async_operation_read_model(
        repository=repository,
        operation_id=operation_id,
    )
    if read_model.operation is None:
        raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
    return to_async_status_response(read_model.operation)


def build_async_operation_replay_view(
    *,
    repository: ProposalRepository,
    operation_id: str,
) -> AdvisoryReplayEvidenceResponse:
    read_model = load_proposal_async_operation_read_model(
        repository=repository,
        operation_id=operation_id,
    )
    if read_model.operation is None:
        raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")

    referents = load_async_operation_replay_referents(
        repository=repository,
        operation=read_model.operation,
    )
    return build_async_operation_replay_response(
        operation=read_model.operation,
        proposal=referents.proposal,
        version=referents.version,
        events=referents.events,
    )


def build_async_operation_correlation_view(
    *,
    repository: ProposalRepository,
    correlation_id: str,
) -> ProposalAsyncOperationStatusResponse:
    read_model = load_proposal_async_operation_by_correlation_read_model(
        repository=repository,
        correlation_id=correlation_id,
    )
    if read_model.operation is None:
        raise ProposalNotFoundError("PROPOSAL_ASYNC_OPERATION_NOT_FOUND")
    return to_async_status_response(read_model.operation)


__all__ = [
    "build_async_operation_correlation_view",
    "build_async_operation_replay_view",
    "build_async_operation_status_view",
]
