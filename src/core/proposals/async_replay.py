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
    if operation.proposal_id is None:
        return AsyncOperationReplayReferents(proposal=None, version=None, events=None)

    proposal = repository.get_proposal(proposal_id=operation.proposal_id)
    version = None
    if proposal is not None and operation.status == "SUCCEEDED":
        version_no = extract_async_result_version_no(operation)
        if version_no is not None:
            version = repository.get_version(
                proposal_id=operation.proposal_id,
                version_no=version_no,
            )
        if version is None:
            version = repository.get_current_version(proposal_id=operation.proposal_id)

    events = None
    if proposal is not None:
        events = repository.list_events(proposal_id=operation.proposal_id)

    return AsyncOperationReplayReferents(proposal=proposal, version=version, events=events)
