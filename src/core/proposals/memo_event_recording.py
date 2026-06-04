from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import ProposalIdempotencyConflictError
from src.core.proposals.memo_persistence_models import (
    ProposalMemoEventRecord,
    ProposalMemoEventType,
    ProposalMemoRecord,
)
from src.core.proposals.repository import ProposalRepository


def memo_event_request_hash(payload: dict[str, Any]) -> str:
    return str(hash_canonical_payload(payload))


def append_or_replay_memo_event(
    *,
    repository: ProposalRepository,
    memo: ProposalMemoRecord,
    event_id: str,
    event_type: ProposalMemoEventType,
    actor_id: str,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
    reason: dict[str, Any],
) -> tuple[ProposalMemoEventRecord, bool]:
    if idempotency_key:
        replayed = find_replayed_memo_event(
            repository=repository,
            memo=memo,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return replayed, True
    event = ProposalMemoEventRecord(
        event_id=event_id,
        memo_id=memo.memo_id,
        proposal_id=memo.proposal_id,
        proposal_version_no=memo.proposal_version_no,
        event_type=event_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json={
            **reason,
            "memo_hash": memo.memo_hash,
            "source_input_hash": memo.source_input_hash,
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
        },
    )
    repository.append_memo_event(event)
    return event, False


def find_replayed_memo_event(
    *,
    repository: ProposalRepository,
    memo: ProposalMemoRecord,
    idempotency_key: str,
    request_hash: str,
) -> ProposalMemoEventRecord | None:
    for event in repository.list_memo_events(memo_id=memo.memo_id):
        if event.reason_json.get("idempotency_key") != idempotency_key:
            continue
        if event.reason_json.get("idempotency_request_hash") != request_hash:
            raise ProposalIdempotencyConflictError("MEMO_EVENT_IDEMPOTENCY_KEY_CONFLICT")
        return event
    return None
