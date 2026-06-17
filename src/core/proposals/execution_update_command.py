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
    ProposalRecord,
    ProposalWorkflowEventRecord,
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
    latest_execution_requested = _required_execution_requested_event(events)
    _validate_execution_update_handoff(
        handoff_event=latest_execution_requested,
        payload=payload,
    )

    request_hash = build_execution_update_request_hash(payload=payload)
    if _is_replayed_execution_update(
        events=events,
        payload=payload,
        request_hash=request_hash,
    ):
        return build_execution_status_response(proposal=proposal, events=events)

    event_type, to_state = resolve_execution_update_event(payload.update_status)
    _validate_execution_update_state(
        proposal=proposal,
        terminal_states=terminal_states,
    )
    occurred_at = _resolve_valid_execution_update_timestamp(
        payload=payload,
        default_occurred_at=default_occurred_at,
        handoff_event=latest_execution_requested,
    )
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


def _required_execution_requested_event(
    events: list[ProposalWorkflowEventRecord],
) -> ProposalWorkflowEventRecord:
    latest_execution_requested = latest_execution_requested_event(events)
    if latest_execution_requested is None:
        raise ProposalValidationError("EXECUTION_HANDOFF_NOT_FOUND")
    return latest_execution_requested


def _validate_execution_update_handoff(
    *,
    handoff_event: ProposalWorkflowEventRecord,
    payload: ProposalExecutionUpdateRequest,
) -> None:
    try:
        validate_execution_update_handoff_identity(
            handoff_event=handoff_event,
            payload=payload,
        )
    except ProposalExecutionUpdateIdentityError as exc:
        raise ProposalStateConflictError(str(exc)) from exc


def _is_replayed_execution_update(
    *,
    events: list[ProposalWorkflowEventRecord],
    payload: ProposalExecutionUpdateRequest,
    request_hash: str,
) -> bool:
    try:
        replay_event = find_replayed_execution_update_event(
            events=events,
            payload=payload,
            request_hash=request_hash,
        )
    except ProposalReplayHashConflictError as exc:
        raise ProposalIdempotencyConflictError(str(exc)) from exc
    return replay_event is not None


def _validate_execution_update_state(
    *,
    proposal: ProposalRecord,
    terminal_states: set[str],
) -> None:
    try:
        validate_execution_update_state(proposal=proposal, terminal_states=terminal_states)
    except ProposalExecutionUpdateTerminalStateError as exc:
        raise ProposalStateConflictError(str(exc)) from exc


def _resolve_valid_execution_update_timestamp(
    *,
    payload: ProposalExecutionUpdateRequest,
    default_occurred_at: datetime,
    handoff_event: ProposalWorkflowEventRecord,
) -> datetime:
    occurred_at = resolve_execution_update_occurred_at(
        payload=payload,
        default_occurred_at=default_occurred_at,
    )
    try:
        validate_execution_update_occurred_after_handoff(
            occurred_at=occurred_at,
            handoff_event=handoff_event,
        )
    except ProposalExecutionUpdateTimestampError as exc:
        raise ProposalValidationError(str(exc)) from exc
    return occurred_at
