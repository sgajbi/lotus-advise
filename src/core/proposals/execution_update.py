from datetime import datetime

from src.core.proposals.models import (
    ProposalExecutionUpdateRequest,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
)


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
        "idempotency_key": f"execution-update:{payload.update_id}",
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
