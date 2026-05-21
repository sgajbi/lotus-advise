from datetime import datetime

from src.core.proposals.activity_read_model import load_proposal_activity_read_model
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalValidationError,
)
from src.core.proposals.execution_status import (
    build_execution_status_response,
    latest_execution_requested_event,
)
from src.core.proposals.execution_update import (
    ProposalExecutionUpdateIdentityError,
    ProposalExecutionUpdateTerminalStateError,
    ProposalExecutionUpdateTimestampError,
    build_execution_update_event_and_apply_state,
    build_execution_update_request_hash,
    find_replayed_execution_update_event,
    resolve_execution_update_occurred_at,
    validate_execution_update_handoff_identity,
    validate_execution_update_occurred_after_handoff,
    validate_execution_update_state,
)
from src.core.proposals.idempotency import ProposalReplayHashConflictError
from src.core.proposals.identifiers import new_workflow_event_id
from src.core.proposals.models import (
    ProposalExecutionStatusResponse,
    ProposalExecutionUpdateRequest,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.transition_persistence import persist_proposal_transition
from src.core.proposals.workflow_rules import resolve_execution_update_event


def record_proposal_execution_update(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    payload: ProposalExecutionUpdateRequest,
    terminal_states: set[str],
    default_occurred_at: datetime,
) -> ProposalExecutionStatusResponse | None:
    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if activity.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    proposal = activity.proposal
    events = activity.events
    latest_execution_requested = latest_execution_requested_event(events)
    if latest_execution_requested is None:
        raise ProposalValidationError("EXECUTION_HANDOFF_NOT_FOUND")

    try:
        validate_execution_update_handoff_identity(
            handoff_event=latest_execution_requested,
            payload=payload,
        )
    except ProposalExecutionUpdateIdentityError as exc:
        raise ProposalStateConflictError(str(exc)) from exc

    request_hash = build_execution_update_request_hash(payload=payload)
    try:
        replay_event = find_replayed_execution_update_event(
            events=events,
            payload=payload,
            request_hash=request_hash,
        )
    except ProposalReplayHashConflictError as exc:
        raise ProposalIdempotencyConflictError(str(exc)) from exc
    if replay_event is not None:
        return build_execution_status_response(proposal=proposal, events=events)

    event_type, to_state = resolve_execution_update_event(payload.update_status)
    try:
        validate_execution_update_state(proposal=proposal, terminal_states=terminal_states)
    except ProposalExecutionUpdateTerminalStateError as exc:
        raise ProposalStateConflictError(str(exc)) from exc

    occurred_at = resolve_execution_update_occurred_at(
        payload=payload,
        default_occurred_at=default_occurred_at,
    )
    try:
        validate_execution_update_occurred_after_handoff(
            occurred_at=occurred_at,
            handoff_event=latest_execution_requested,
        )
    except ProposalExecutionUpdateTimestampError as exc:
        raise ProposalValidationError(str(exc)) from exc
    event = build_execution_update_event_and_apply_state(
        event_id=new_workflow_event_id(),
        proposal=proposal,
        payload=payload,
        event_type=event_type,
        to_state=to_state,
        occurred_at=occurred_at,
        request_hash=request_hash,
        handoff_related_version_no=latest_execution_requested.related_version_no,
    )
    persist_proposal_transition(
        repository=repository,
        proposal=proposal,
        event=event,
    )
    return None
