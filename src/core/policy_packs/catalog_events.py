from datetime import UTC, datetime
from typing import Any

from src.core.policy_packs.catalog_definitions import CATALOG_CONTRACT_VERSION
from src.core.policy_packs.catalog_models import PolicyPackAuditEvent
from src.core.proposals.exceptions import ProposalIdempotencyConflictError


def append_policy_pack_catalog_event(
    *,
    events: dict[tuple[str, str], list[PolicyPackAuditEvent]],
    idempotency: dict[str, tuple[str, PolicyPackAuditEvent]],
    event_type: str,
    policy_pack_id: str,
    policy_version: str,
    actor_id: str,
    content_hash: str,
    idempotency_key: str,
    request_hash: str,
    reason: dict[str, Any],
) -> PolicyPackAuditEvent:
    key = (policy_pack_id, policy_version)
    event = PolicyPackAuditEvent(
        event_id=f"ppev_{len(events[key]) + 1:06d}",
        event_type=event_type,
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
        actor_id=actor_id,
        occurred_at=datetime.now(UTC).isoformat(),
        content_hash=content_hash,
        idempotency_key=idempotency_key,
        reason={
            **reason,
            "idempotency_request_hash": request_hash,
            "catalog_contract_version": CATALOG_CONTRACT_VERSION,
        },
    )
    events[key].append(event)
    idempotency[idempotency_key] = (request_hash, event)
    return event


def find_replayed_policy_pack_catalog_event(
    *,
    idempotency: dict[str, tuple[str, PolicyPackAuditEvent]],
    idempotency_key: str,
    request_hash: str,
) -> PolicyPackAuditEvent | None:
    stored = idempotency.get(idempotency_key)
    if stored is None:
        return None
    stored_hash, event = stored
    if stored_hash != request_hash:
        raise ProposalIdempotencyConflictError("POLICY_PACK_IDEMPOTENCY_KEY_CONFLICT")
    return event


def latest_policy_pack_validation_event(
    *,
    events: dict[tuple[str, str], list[PolicyPackAuditEvent]],
    policy_pack_id: str,
    policy_version: str,
) -> PolicyPackAuditEvent | None:
    for event in reversed(events[(policy_pack_id, policy_version)]):
        if event.event_type == "POLICY_PACK_VALIDATED":
            return event
    return None
