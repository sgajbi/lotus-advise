from collections.abc import Callable
from datetime import datetime

from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.api_models import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitAcknowledgeResponse,
)
from src.core.advisor_cockpit.persistence import (
    CockpitAcknowledgementIdempotencyRecord,
    CockpitAcknowledgementRecord,
)
from src.core.advisor_cockpit.projection_bounds import bounded_reference
from src.core.advisor_cockpit.reference_models import CockpitAcknowledgementState
from src.core.advisor_cockpit.repository import AdvisorCockpitRepository
from src.core.advisor_cockpit.rules import apply_cockpit_acknowledgement_state
from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key

COCKPIT_ACKNOWLEDGEMENT_OPERATION = "ACKNOWLEDGE_COCKPIT_ACTION"


def acknowledge_cockpit_action(
    *,
    repository: AdvisorCockpitRepository,
    now_fn: Callable[[], datetime],
    action: AdvisoryActionItem,
    action_item_id: str,
    payload: AdvisorCockpitAcknowledgeRequest,
    idempotency_key: str,
    correlation_id: str | None,
    contract_version: str,
) -> AdvisorCockpitAcknowledgeResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    if payload.action_item_version != action.action_item_version:
        raise ProposalValidationError("ADVISOR_COCKPIT_ACTION_VERSION_STALE")

    request_hash = hash_canonical_payload(
        {
            "contract_version": contract_version,
            "operation": COCKPIT_ACKNOWLEDGEMENT_OPERATION,
            "action_item_id": action_item_id,
            "action_item_version": payload.action_item_version,
            "acknowledged_by": payload.acknowledged_by,
            "acknowledgement_note": payload.acknowledgement_note,
        }
    )
    replayed = repository.get_cockpit_acknowledgement_idempotency(idempotency_key=idempotency_key)
    if replayed is not None:
        if replayed.request_hash != request_hash:
            raise ProposalIdempotencyConflictError(
                "ADVISOR_COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_CONFLICT"
            )
        record = repository.get_cockpit_acknowledgement(action_item_id=replayed.action_item_id)
        if record is None:
            raise ProposalNotFoundError("ADVISOR_COCKPIT_ACKNOWLEDGEMENT_NOT_FOUND")
        return acknowledgement_response(
            action=action,
            record=record,
            replayed=True,
            contract_version=contract_version,
        )

    acknowledged_at = now_fn()
    record = CockpitAcknowledgementRecord(
        acknowledgement_id=bounded_reference(f"ack_{action_item_id}"),
        action_item_id=action_item_id,
        action_item_version=payload.action_item_version,
        acknowledged_by=payload.acknowledged_by,
        acknowledged_at=acknowledged_at,
        acknowledgement_note=payload.acknowledgement_note,
        correlation_id=correlation_id,
        reason_json={
            "contract_version": contract_version,
            "idempotency_key": idempotency_key,
            "request_hash": request_hash,
            "owner_role": action.owner_role,
            "status_after_acknowledgement": action.status,
        },
    )
    try:
        repository.save_cockpit_acknowledgement_with_idempotency(
            acknowledgement=record,
            idempotency=CockpitAcknowledgementIdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                acknowledgement_id=record.acknowledgement_id,
                action_item_id=action_item_id,
                created_at=acknowledged_at,
            ),
        )
    except ValueError as exc:
        raise ProposalIdempotencyConflictError(
            "ADVISOR_COCKPIT_ACKNOWLEDGEMENT_IDEMPOTENCY_CONFLICT"
        ) from exc
    return acknowledgement_response(
        action=action,
        record=record,
        replayed=False,
        contract_version=contract_version,
    )


def acknowledgement_response(
    *,
    action: AdvisoryActionItem,
    record: CockpitAcknowledgementRecord,
    replayed: bool,
    contract_version: str,
) -> AdvisorCockpitAcknowledgeResponse:
    acknowledgement = acknowledgement_state(record)
    return AdvisorCockpitAcknowledgeResponse(
        action_item=apply_cockpit_acknowledgement_state(action, acknowledgement),
        acknowledgement=acknowledgement,
        replayed=replayed,
        audit={
            "acknowledgement_id": record.acknowledgement_id,
            "correlation_id": record.correlation_id,
            "contract_version": contract_version,
            "idempotency_key": record.reason_json.get("idempotency_key"),
        },
    )


def acknowledgement_state(
    record: CockpitAcknowledgementRecord,
) -> CockpitAcknowledgementState:
    return CockpitAcknowledgementState(
        acknowledged=True,
        acknowledgement_id=record.acknowledgement_id,
        acknowledged_by=record.acknowledged_by,
        acknowledged_at=record.acknowledged_at.isoformat(),
        acknowledgement_note=record.acknowledgement_note,
    )


__all__ = [
    "acknowledge_cockpit_action",
    "acknowledgement_response",
    "acknowledgement_state",
]
