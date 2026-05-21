from collections.abc import Collection
from datetime import datetime

from src.core.proposals.models import (
    ProposalExecutionUpdateRequest,
    ProposalRecord,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
)


class ProposalExecutionUpdateIdentityError(Exception):
    pass


class ProposalExecutionUpdateRequestIdMismatchError(ProposalExecutionUpdateIdentityError):
    pass


class ProposalExecutionUpdateProviderMismatchError(ProposalExecutionUpdateIdentityError):
    pass


class ProposalExecutionUpdateTerminalStateError(Exception):
    pass


class ProposalExecutionUpdateTimestampError(Exception):
    pass


def build_execution_update_idempotency_key(*, payload: ProposalExecutionUpdateRequest) -> str:
    return f"execution-update:{payload.update_id}"


def validate_execution_update_handoff_identity(
    *,
    handoff_event: ProposalWorkflowEventRecord,
    payload: ProposalExecutionUpdateRequest,
) -> None:
    expected_execution_request_id = handoff_event.reason_json.get("execution_request_id")
    if expected_execution_request_id != payload.execution_request_id:
        raise ProposalExecutionUpdateRequestIdMismatchError("EXECUTION_REQUEST_ID_MISMATCH")
    expected_execution_provider = handoff_event.reason_json.get("execution_provider")
    if expected_execution_provider != payload.execution_provider:
        raise ProposalExecutionUpdateProviderMismatchError("EXECUTION_PROVIDER_MISMATCH")


def validate_execution_update_state(
    *,
    proposal: ProposalRecord,
    terminal_states: Collection[str],
) -> None:
    if proposal.current_state in terminal_states:
        raise ProposalExecutionUpdateTerminalStateError(
            "PROPOSAL_TERMINAL_STATE: execution update rejected"
        )


def validate_execution_update_occurred_after_handoff(
    *,
    occurred_at: datetime,
    handoff_event: ProposalWorkflowEventRecord,
) -> None:
    if occurred_at < handoff_event.occurred_at:
        raise ProposalExecutionUpdateTimestampError("EXECUTION_UPDATE_OCCURRED_BEFORE_HANDOFF")


def resolve_execution_update_occurred_at(
    *,
    payload: ProposalExecutionUpdateRequest,
    default_occurred_at: datetime,
) -> datetime:
    if payload.occurred_at is not None:
        return datetime.fromisoformat(payload.occurred_at)
    return default_occurred_at


def build_execution_update_event(
    *,
    event_id: str,
    proposal_id: str,
    current_state: ProposalWorkflowState,
    payload: ProposalExecutionUpdateRequest,
    event_type: str,
    to_state: ProposalWorkflowState,
    occurred_at: datetime,
    request_hash: str,
    handoff_related_version_no: int | None,
) -> ProposalWorkflowEventRecord:
    reason_json = {
        "update_id": payload.update_id,
        "execution_request_id": payload.execution_request_id,
        "execution_provider": payload.execution_provider,
        "external_execution_id": payload.external_execution_id,
        "details": payload.details,
        "idempotency_key": build_execution_update_idempotency_key(payload=payload),
        "idempotency_request_hash": request_hash,
    }
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal_id,
        event_type=event_type,
        from_state=current_state,
        to_state=to_state,
        actor_id=payload.actor_id,
        occurred_at=occurred_at,
        reason_json={key: value for key, value in reason_json.items() if value is not None},
        related_version_no=payload.related_version_no or handoff_related_version_no,
    )


def apply_execution_update_state(
    *,
    proposal: ProposalRecord,
    to_state: ProposalWorkflowState,
    event: ProposalWorkflowEventRecord,
) -> None:
    proposal.current_state = to_state
    proposal.last_event_at = event.occurred_at
