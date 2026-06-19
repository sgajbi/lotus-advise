from dataclasses import dataclass

from src.core.proposals.async_operations import extract_async_result_version_no
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class AsyncOperationReplayReferents:
    proposal: ProposalRecord | None
    version: ProposalVersionRecord | None
    events: list[ProposalWorkflowEventRecord] | None


def load_async_operation_replay_referents(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
) -> AsyncOperationReplayReferents:
    proposal_id = operation.proposal_id
    if proposal_id is None:
        return _empty_replay_referents()

    proposal = repository.get_proposal(proposal_id=proposal_id)
    return AsyncOperationReplayReferents(
        proposal=proposal,
        version=_load_succeeded_version(
            repository=repository,
            operation=operation,
            proposal_id=proposal_id,
            proposal=proposal,
        ),
        events=_load_proposal_events(
            repository=repository,
            proposal_id=proposal_id,
            proposal=proposal,
        ),
    )


def _empty_replay_referents() -> AsyncOperationReplayReferents:
    return AsyncOperationReplayReferents(proposal=None, version=None, events=None)


def _load_succeeded_version(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    proposal_id: str,
    proposal: ProposalRecord | None,
) -> ProposalVersionRecord | None:
    if proposal is None or operation.status != "SUCCEEDED":
        return None

    result_version = _load_result_version(
        repository=repository,
        operation=operation,
        proposal_id=proposal_id,
    )
    if result_version is not None:
        return result_version

    return repository.get_current_version(proposal_id=proposal_id)


def _load_result_version(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    proposal_id: str,
) -> ProposalVersionRecord | None:
    version_no = extract_async_result_version_no(operation)
    if version_no is None:
        return None

    return repository.get_version(
        proposal_id=proposal_id,
        version_no=version_no,
    )


def _load_proposal_events(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    proposal: ProposalRecord | None,
) -> list[ProposalWorkflowEventRecord] | None:
    if proposal is None:
        return None

    return repository.list_events(proposal_id=proposal_id)
