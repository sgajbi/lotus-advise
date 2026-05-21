from datetime import datetime
from typing import cast

from src.core.common.canonical import hash_canonical_payload
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


def build_state_transition_request_hash(*, payload: ProposalStateTransitionRequest) -> str:
    return cast(str, hash_canonical_payload(payload.model_dump(mode="json")))


def build_proposal_created_event(
    *,
    event_id: str,
    proposal_id: str,
    actor_id: str,
    occurred_at: datetime,
    related_version_no: int,
    correlation_id: str | None,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal_id,
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json={"correlation_id": correlation_id} if correlation_id else {},
        related_version_no=related_version_no,
    )


def build_new_version_created_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    actor_id: str,
    occurred_at: datetime,
    related_version_no: int,
    correlation_id: str | None,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type="NEW_VERSION_CREATED",
        from_state=proposal.current_state,
        to_state="DRAFT",
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json={"correlation_id": correlation_id} if correlation_id else {},
        related_version_no=related_version_no,
    )


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


def apply_lifecycle_transition_state(
    *,
    proposal: ProposalRecord,
    to_state: ProposalWorkflowState,
    event: ProposalWorkflowEventRecord,
) -> None:
    proposal.current_state = to_state
    proposal.last_event_at = event.occurred_at


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
