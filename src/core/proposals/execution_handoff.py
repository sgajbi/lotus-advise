from datetime import datetime
from typing import cast

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.execution_boundary import execution_ownership_boundary
from src.core.proposals.models import (
    ProposalExecutionHandoffRequest,
    ProposalExecutionHandoffResponse,
    ProposalRecord,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
)
from src.core.proposals.projections import to_proposal_summary, to_workflow_event


class ProposalExecutionHandoffStateError(Exception):
    pass


def build_execution_handoff_request_hash(*, payload: ProposalExecutionHandoffRequest) -> str:
    return cast(str, hash_canonical_payload(payload.model_dump(mode="json")))


def validate_execution_handoff_ready(*, current_state: ProposalWorkflowState) -> None:
    if current_state != "EXECUTION_READY":
        raise ProposalExecutionHandoffStateError(
            "STATE_CONFLICT: proposal must be EXECUTION_READY for execution handoff"
        )


def build_execution_handoff_replay_response(
    *,
    proposal: ProposalRecord,
    replay_event: ProposalWorkflowEventRecord,
) -> ProposalExecutionHandoffResponse:
    execution_request_id = replay_event.reason_json.get("execution_request_id")
    return ProposalExecutionHandoffResponse(
        proposal=to_proposal_summary(proposal),
        execution_request_id=str(execution_request_id) if execution_request_id is not None else "",
        handoff_status="REQUESTED",
        execution_provider=str(replay_event.reason_json.get("execution_provider")),
        latest_workflow_event=to_workflow_event(replay_event),
    )


def build_execution_handoff_requested_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    payload: ProposalExecutionHandoffRequest,
    occurred_at: datetime,
    execution_request_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord:
    reason_json = {
        "execution_request_id": execution_request_id,
        "execution_provider": payload.execution_provider,
        "correlation_id": payload.correlation_id,
        "external_request_id": payload.external_request_id,
        "execution_ownership": execution_ownership_boundary(),
        "notes": payload.notes,
    }
    if idempotency_key:
        reason_json["idempotency_key"] = idempotency_key
        reason_json["idempotency_request_hash"] = request_hash

    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type="EXECUTION_REQUESTED",
        from_state=proposal.current_state,
        to_state="EXECUTION_READY",
        actor_id=payload.actor_id,
        occurred_at=occurred_at,
        reason_json={key: value for key, value in reason_json.items() if value is not None},
        related_version_no=payload.related_version_no or proposal.current_version_no,
    )


def apply_execution_handoff_state(
    *,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
) -> None:
    proposal.last_event_at = event.occurred_at


def build_execution_handoff_event_and_apply_state(
    *,
    event_id: str,
    proposal: ProposalRecord,
    payload: ProposalExecutionHandoffRequest,
    occurred_at: datetime,
    execution_request_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord:
    event = build_execution_handoff_requested_event(
        event_id=event_id,
        proposal=proposal,
        payload=payload,
        occurred_at=occurred_at,
        execution_request_id=execution_request_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    apply_execution_handoff_state(proposal=proposal, event=event)
    return event


def build_execution_handoff_response(
    *,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
    execution_request_id: str,
    execution_provider: str,
) -> ProposalExecutionHandoffResponse:
    return ProposalExecutionHandoffResponse(
        proposal=to_proposal_summary(proposal),
        execution_request_id=execution_request_id,
        handoff_status="REQUESTED",
        execution_provider=execution_provider,
        latest_workflow_event=to_workflow_event(event),
    )
