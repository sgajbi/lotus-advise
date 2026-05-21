from datetime import datetime

from src.core.proposals.command_read_model import load_proposal_command_read_model
from src.core.proposals.command_validation import validate_proposal_expected_state
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
)
from src.core.proposals.execution_handoff import (
    ProposalExecutionHandoffStateError,
    build_execution_handoff_event_and_apply_state,
    build_execution_handoff_replay_response,
    build_execution_handoff_request_hash,
    build_execution_handoff_response,
    validate_execution_handoff_ready,
)
from src.core.proposals.idempotency import (
    ProposalReplayHashConflictError,
    load_replayed_event,
)
from src.core.proposals.identifiers import new_execution_request_id, new_workflow_event_id
from src.core.proposals.models import (
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.transition_persistence import persist_proposal_transition


def request_proposal_execution_handoff(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    payload: ProposalExecutionHandoffRequest,
    idempotency_key: str | None,
    require_expected_state: bool,
    occurred_at: datetime,
) -> ProposalExecutionHandoffResponse:
    command_read_model = load_proposal_command_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if command_read_model.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    proposal = command_read_model.proposal
    request_hash = build_execution_handoff_request_hash(payload=payload)
    replay_event = _load_replayed_execution_handoff_event(
        repository=repository,
        proposal_id=proposal_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replay_event is not None:
        return build_execution_handoff_replay_response(
            proposal=proposal,
            replay_event=replay_event,
        )
    validate_proposal_expected_state(
        current_state=proposal.current_state,
        expected_state=payload.expected_state,
        require_expected_state=require_expected_state,
    )
    try:
        validate_execution_handoff_ready(current_state=proposal.current_state)
    except ProposalExecutionHandoffStateError as exc:
        raise ProposalStateConflictError(str(exc)) from exc

    execution_request_id = payload.external_request_id or new_execution_request_id()
    event = build_execution_handoff_event_and_apply_state(
        event_id=new_workflow_event_id(),
        proposal=proposal,
        payload=payload,
        occurred_at=occurred_at,
        execution_request_id=execution_request_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    result = persist_proposal_transition(
        repository=repository,
        proposal=proposal,
        event=event,
    )
    return build_execution_handoff_response(
        proposal=result.proposal,
        event=result.event,
        execution_request_id=execution_request_id,
        execution_provider=payload.execution_provider,
    )


def _load_replayed_execution_handoff_event(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
):
    try:
        return load_replayed_event(
            repository=repository,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except ProposalReplayHashConflictError as exc:
        raise ProposalIdempotencyConflictError(str(exc)) from exc
