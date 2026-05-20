from collections.abc import Sequence

from src.core.proposals.models import ProposalApprovalRecordData, ProposalWorkflowEventRecord


class ProposalReplayHashConflictError(ValueError):
    pass


def find_replayed_event(
    *,
    events: Sequence[ProposalWorkflowEventRecord],
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord | None:
    if not idempotency_key:
        return None
    for event in reversed(events):
        existing_key = event.reason_json.get("idempotency_key")
        if existing_key != idempotency_key:
            continue
        existing_hash = event.reason_json.get("idempotency_request_hash")
        if existing_hash is not None and existing_hash != request_hash:
            raise ProposalReplayHashConflictError("IDEMPOTENCY_KEY_CONFLICT: request hash mismatch")
        return event
    return None


def find_replayed_approval(
    *,
    approvals: Sequence[ProposalApprovalRecordData],
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalApprovalRecordData | None:
    if not idempotency_key:
        return None
    for approval in reversed(approvals):
        existing_key = approval.details_json.get("idempotency_key")
        if existing_key != idempotency_key:
            continue
        existing_hash = approval.details_json.get("idempotency_request_hash")
        if existing_hash is not None and existing_hash != request_hash:
            raise ProposalReplayHashConflictError("IDEMPOTENCY_KEY_CONFLICT: request hash mismatch")
        return approval
    return None
