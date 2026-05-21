from src.core.proposals.models import ProposalVersionRecord
from src.core.proposals.records import ProposalCreateCommandState
from src.core.proposals.repository import ProposalRepository


def persist_created_proposal(
    *,
    repository: ProposalRepository,
    command_state: ProposalCreateCommandState,
    version: ProposalVersionRecord,
) -> None:
    repository.create_proposal(command_state.proposal)
    repository.create_version(version)
    repository.append_event(command_state.created_event)
    repository.save_idempotency(command_state.idempotency_record)
