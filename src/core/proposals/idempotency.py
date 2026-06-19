from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

from src.core.proposals.models import ProposalApprovalRecordData, ProposalWorkflowEventRecord
from src.core.proposals.repository import ProposalRepository

_ReplayRecord = TypeVar("_ReplayRecord")


class ProposalReplayHashConflictError(ValueError):
    pass


def _find_replayed_record(
    *,
    records: Sequence[_ReplayRecord],
    idempotency_key: str | None,
    request_hash: str,
    metadata: Callable[[_ReplayRecord], Mapping[str, object]],
) -> _ReplayRecord | None:
    if not idempotency_key:
        return None
    for record in reversed(records):
        record_metadata = metadata(record)
        if _metadata_matches_replay(
            record_metadata,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ):
            return record
    return None


def _metadata_matches_replay(
    metadata: Mapping[str, object],
    *,
    idempotency_key: str,
    request_hash: str,
) -> bool:
    if metadata.get("idempotency_key") != idempotency_key:
        return False
    existing_hash = metadata.get("idempotency_request_hash")
    if existing_hash is not None and existing_hash != request_hash:
        raise ProposalReplayHashConflictError("IDEMPOTENCY_KEY_CONFLICT: request hash mismatch")
    return True


def find_replayed_event(
    *,
    events: Sequence[ProposalWorkflowEventRecord],
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord | None:
    return _find_replayed_record(
        records=events,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        metadata=lambda event: event.reason_json,
    )


def load_replayed_event(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalWorkflowEventRecord | None:
    return find_replayed_event(
        events=repository.list_events(proposal_id=proposal_id),
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )


def find_replayed_approval(
    *,
    approvals: Sequence[ProposalApprovalRecordData],
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalApprovalRecordData | None:
    return _find_replayed_record(
        records=approvals,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        metadata=lambda approval: approval.details_json,
    )


def load_replayed_approval(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalApprovalRecordData | None:
    return find_replayed_approval(
        approvals=repository.list_approvals(proposal_id=proposal_id),
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
