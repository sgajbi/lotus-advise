from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

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
    _validate_acknowledgement_version(action=action, payload=payload)
    request_hash = _acknowledgement_request_hash(
        contract_version=contract_version,
        action_item_id=action_item_id,
        payload=payload,
    )
    replay_response = _acknowledgement_replay_response(
        repository=repository,
        action=action,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        contract_version=contract_version,
    )
    if replay_response is not None:
        return replay_response

    acknowledged_at = now_fn()
    record = _acknowledgement_record(
        action=action,
        action_item_id=action_item_id,
        acknowledged_at=acknowledged_at,
        payload=payload,
        correlation_id=correlation_id,
        contract_version=contract_version,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    _save_acknowledgement(
        repository=repository,
        record=record,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        action_item_id=action_item_id,
        acknowledged_at=acknowledged_at,
    )
    return acknowledgement_response(
        action=action,
        record=record,
        replayed=False,
        contract_version=contract_version,
    )


def _validate_acknowledgement_version(
    *,
    action: AdvisoryActionItem,
    payload: AdvisorCockpitAcknowledgeRequest,
) -> None:
    if payload.action_item_version != action.action_item_version:
        raise ProposalValidationError("ADVISOR_COCKPIT_ACTION_VERSION_STALE")


def _acknowledgement_request_hash(
    *,
    contract_version: str,
    action_item_id: str,
    payload: AdvisorCockpitAcknowledgeRequest,
) -> str:
    return cast(
        str,
        hash_canonical_payload(
            {
                "contract_version": contract_version,
                "operation": COCKPIT_ACKNOWLEDGEMENT_OPERATION,
                "action_item_id": action_item_id,
                "action_item_version": payload.action_item_version,
                "acknowledged_by": payload.acknowledged_by,
                "acknowledgement_note": payload.acknowledgement_note,
            }
        ),
    )


def _acknowledgement_replay_response(
    *,
    repository: AdvisorCockpitRepository,
    action: AdvisoryActionItem,
    idempotency_key: str,
    request_hash: str,
    contract_version: str,
) -> AdvisorCockpitAcknowledgeResponse | None:
    replayed = repository.get_cockpit_acknowledgement_idempotency(idempotency_key=idempotency_key)
    if replayed is None:
        return None
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


def _acknowledgement_record(
    *,
    action: AdvisoryActionItem,
    action_item_id: str,
    acknowledged_at: datetime,
    payload: AdvisorCockpitAcknowledgeRequest,
    correlation_id: str | None,
    contract_version: str,
    idempotency_key: str,
    request_hash: str,
) -> CockpitAcknowledgementRecord:
    return CockpitAcknowledgementRecord(
        acknowledgement_id=bounded_reference(f"ack_{action_item_id}"),
        action_item_id=action_item_id,
        action_item_version=payload.action_item_version,
        acknowledged_by=payload.acknowledged_by,
        acknowledged_at=acknowledged_at,
        acknowledgement_note=payload.acknowledgement_note,
        correlation_id=correlation_id,
        reason_json=_acknowledgement_reason_json(
            action=action,
            contract_version=contract_version,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ),
    )


def _acknowledgement_reason_json(
    *,
    action: AdvisoryActionItem,
    contract_version: str,
    idempotency_key: str,
    request_hash: str,
) -> dict[str, Any]:
    return {
        "contract_version": contract_version,
        "idempotency_key": idempotency_key,
        "request_hash": request_hash,
        "owner_role": action.owner_role,
        "status_after_acknowledgement": action.status,
    }


def _save_acknowledgement(
    *,
    repository: AdvisorCockpitRepository,
    record: CockpitAcknowledgementRecord,
    idempotency_key: str,
    request_hash: str,
    action_item_id: str,
    acknowledged_at: datetime,
) -> None:
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
