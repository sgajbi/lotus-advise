from datetime import datetime

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalApprovalRequest,
    ProposalRecord,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalWorkflowEventRecord,
    ProposalWorkflowState,
)
from src.core.proposals.projections import to_approval_record, to_workflow_event


def build_state_transition_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    payload: ProposalStateTransitionRequest,
    to_state: ProposalWorkflowState,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord:
    reason_json = dict(payload.reason)
    if idempotency_key:
        reason_json["idempotency_key"] = idempotency_key
        reason_json["idempotency_request_hash"] = request_hash
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type=payload.event_type,
        from_state=proposal.current_state,
        to_state=to_state,
        actor_id=payload.actor_id,
        occurred_at=occurred_at,
        reason_json=reason_json,
        related_version_no=payload.related_version_no,
    )


def build_state_transition_response(
    *,
    proposal_id: str,
    current_state: ProposalWorkflowState,
    event: ProposalWorkflowEventRecord,
) -> ProposalStateTransitionResponse:
    return ProposalStateTransitionResponse(
        proposal_id=proposal_id,
        current_state=current_state,
        latest_workflow_event=to_workflow_event(event),
    )


def build_approval_record(
    *,
    approval_id: str,
    proposal_id: str,
    payload: ProposalApprovalRequest,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalApprovalRecordData:
    details_json = dict(payload.details)
    if idempotency_key:
        details_json["idempotency_key"] = idempotency_key
        details_json["idempotency_request_hash"] = request_hash
    return ProposalApprovalRecordData(
        approval_id=approval_id,
        proposal_id=proposal_id,
        approval_type=payload.approval_type,
        approved=payload.approved,
        actor_id=payload.actor_id,
        occurred_at=occurred_at,
        details_json=details_json,
        related_version_no=payload.related_version_no,
    )


def build_approval_transition_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    payload: ProposalApprovalRequest,
    event_type: str,
    to_state: ProposalWorkflowState,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord:
    reason_json = dict(payload.details)
    if idempotency_key:
        reason_json["idempotency_key"] = idempotency_key
        reason_json["idempotency_request_hash"] = request_hash
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type=event_type,
        from_state=proposal.current_state,
        to_state=to_state,
        actor_id=payload.actor_id,
        occurred_at=occurred_at,
        reason_json=reason_json,
        related_version_no=payload.related_version_no,
    )


def build_approval_transition_response(
    *,
    proposal_id: str,
    current_state: ProposalWorkflowState,
    event: ProposalWorkflowEventRecord,
    approval: ProposalApprovalRecordData | None,
) -> ProposalStateTransitionResponse:
    return ProposalStateTransitionResponse(
        proposal_id=proposal_id,
        current_state=current_state,
        latest_workflow_event=to_workflow_event(event),
        approval=to_approval_record(approval),
    )
