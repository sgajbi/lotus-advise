from datetime import datetime

from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.proposals.command_read_model import load_proposal_command_read_model
from src.core.proposals.command_validation import (
    resolve_proposal_approval_transition,
    resolve_proposal_transition_state,
    validate_proposal_expected_state,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalLifecycleError,
    ProposalNotFoundError,
)
from src.core.proposals.idempotency import (
    ProposalReplayHashConflictError,
    load_replayed_approval,
    load_replayed_event,
)
from src.core.proposals.identifiers import new_approval_id, new_workflow_event_id
from src.core.proposals.lifecycle_events import (
    build_approval_command_state_and_apply_transition,
    build_approval_replay_response_from_referents,
    build_approval_request_hash,
    build_approval_transition_response,
    build_state_transition_event_and_apply_state,
    build_state_transition_replay_response,
    build_state_transition_request_hash,
    build_state_transition_response,
)
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.transition_persistence import (
    persist_proposal_approval_transition,
    persist_proposal_transition,
)


def transition_proposal_state(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    payload: ProposalStateTransitionRequest,
    idempotency_key: str | None,
    require_expected_state: bool,
    occurred_at: datetime,
) -> ProposalStateTransitionResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    command_read_model = load_proposal_command_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if command_read_model.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    proposal = command_read_model.proposal
    request_hash = build_state_transition_request_hash(payload=payload)
    replay_event = _load_replayed_event(
        repository=repository,
        proposal_id=proposal_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replay_event is not None:
        return build_state_transition_replay_response(
            proposal_id=proposal_id,
            event=replay_event,
        )
    validate_proposal_expected_state(
        current_state=proposal.current_state,
        expected_state=payload.expected_state,
        require_expected_state=require_expected_state,
    )

    to_state = resolve_proposal_transition_state(
        current_state=proposal.current_state,
        event_type=payload.event_type,
    )
    event = build_state_transition_event_and_apply_state(
        event_id=new_workflow_event_id(),
        proposal=proposal,
        payload=payload,
        to_state=to_state,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    result = persist_proposal_transition(
        repository=repository,
        proposal=proposal,
        event=event,
    )
    return build_state_transition_response(
        proposal_id=proposal_id,
        current_state=result.proposal.current_state,
        event=result.event,
    )


def record_proposal_approval(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    payload: ProposalApprovalRequest,
    idempotency_key: str | None,
    require_expected_state: bool,
    occurred_at: datetime,
) -> ProposalStateTransitionResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    command_read_model = load_proposal_command_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if command_read_model.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    proposal = command_read_model.proposal
    request_hash = build_approval_request_hash(payload=payload)
    replay_approval = _load_replayed_approval(
        repository=repository,
        proposal_id=proposal_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replay_approval is not None:
        replay_event = _load_replayed_event(
            repository=repository,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        replay_response = build_approval_replay_response_from_referents(
            proposal_id=proposal_id,
            approval=replay_approval,
            event=replay_event,
        )
        if replay_response is None:
            raise ProposalLifecycleError("PROPOSAL_IDEMPOTENCY_REFERENT_NOT_FOUND")
        return replay_response
    validate_proposal_expected_state(
        current_state=proposal.current_state,
        expected_state=payload.expected_state,
        require_expected_state=require_expected_state,
    )

    event_type, to_state = resolve_proposal_approval_transition(
        current_state=proposal.current_state,
        approval_type=payload.approval_type,
        approved=payload.approved,
    )
    command_state = build_approval_command_state_and_apply_transition(
        approval_id=new_approval_id(),
        event_id=new_workflow_event_id(),
        proposal=proposal,
        payload=payload,
        event_type=event_type,
        to_state=to_state,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )

    result = persist_proposal_approval_transition(
        repository=repository,
        proposal=proposal,
        event=command_state.event,
        approval=command_state.approval,
    )
    return build_approval_transition_response(
        proposal_id=proposal_id,
        current_state=result.proposal.current_state,
        event=result.event,
        approval=result.approval,
    )


def _load_replayed_event(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord | None:
    try:
        return load_replayed_event(
            repository=repository,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except ProposalReplayHashConflictError as exc:
        raise ProposalIdempotencyConflictError(str(exc)) from exc


def _load_replayed_approval(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalApprovalRecordData | None:
    try:
        return load_replayed_approval(
            repository=repository,
            proposal_id=proposal_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except ProposalReplayHashConflictError as exc:
        raise ProposalIdempotencyConflictError(str(exc)) from exc
