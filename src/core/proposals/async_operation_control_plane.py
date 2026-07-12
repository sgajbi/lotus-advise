from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Sequence, cast

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.contract_types import (
    ProposalAsyncOperationStatus,
    ProposalAsyncOperationType,
)
from src.core.proposals.models import ProposalAsyncOperationRecord

ASYNC_OPERATION_CONTROL_CAPABILITY = "advisory.proposals.async_operations.control"
ASYNC_OPERATION_CONTROL_MAX_LIST_LIMIT = 50
ASYNC_OPERATION_QUARANTINED_CODE = "PROPOSAL_ASYNC_OPERATION_QUARANTINED"

AsyncOperationControlAction = Literal["DRY_RUN", "RETRY", "QUARANTINE", "PAUSE_DRAIN"]
AsyncOperationControlStatus = Literal[
    "PENDING",
    "LEASED",
    "RECOVERABLE_STUCK",
    "RETRY_EXHAUSTED",
    "QUARANTINED",
    "TERMINAL_FAILED",
    "TERMINAL_SUCCEEDED",
]


@dataclass(frozen=True)
class AsyncOperationControlPrincipal:
    actor_id: str
    role: str
    tenant_id: str
    legal_entity_code: str
    service_identity: str
    capabilities: frozenset[str]
    principal_status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"


@dataclass(frozen=True)
class AsyncOperationControlFilters:
    control_statuses: tuple[AsyncOperationControlStatus, ...] = (
        "PENDING",
        "LEASED",
        "RECOVERABLE_STUCK",
        "RETRY_EXHAUSTED",
        "QUARANTINED",
    )
    operation_types: tuple[ProposalAsyncOperationType, ...] = (
        "CREATE_PROPOSAL",
        "CREATE_PROPOSAL_VERSION",
    )
    limit: int = ASYNC_OPERATION_CONTROL_MAX_LIST_LIMIT


@dataclass(frozen=True)
class AsyncOperationControlListItem:
    operation_id: str
    operation_type: ProposalAsyncOperationType
    status: ProposalAsyncOperationStatus
    control_status: AsyncOperationControlStatus
    correlation_id: str
    proposal_id: str | None
    created_at: datetime
    started_at: datetime | None
    lease_expires_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    max_attempts: int


@dataclass(frozen=True)
class AsyncOperationControlDecision:
    allowed: bool
    action: AsyncOperationControlAction
    reason_code: str
    control_status: AsyncOperationControlStatus
    target_status: ProposalAsyncOperationStatus | None
    schedule_execution: bool
    payload_mutation_allowed: bool
    audit_event: dict[str, object]
    idempotent_noop: bool = False


def normalize_async_operation_control_filters(
    filters: AsyncOperationControlFilters,
) -> AsyncOperationControlFilters:
    return AsyncOperationControlFilters(
        control_statuses=tuple(dict.fromkeys(filters.control_statuses)),
        operation_types=tuple(dict.fromkeys(filters.operation_types)),
        limit=max(0, min(filters.limit, ASYNC_OPERATION_CONTROL_MAX_LIST_LIMIT)),
    )


def list_async_operations_for_control(
    operations: Sequence[ProposalAsyncOperationRecord],
    *,
    filters: AsyncOperationControlFilters,
    as_of: datetime,
) -> list[AsyncOperationControlListItem]:
    normalized = normalize_async_operation_control_filters(filters)
    if normalized.limit <= 0:
        return []

    items = [
        _to_list_item(operation=operation, as_of=as_of)
        for operation in operations
        if operation.operation_type in normalized.operation_types
    ]
    selected = [item for item in items if item.control_status in normalized.control_statuses]
    selected.sort(key=lambda item: (item.created_at, item.operation_id))
    return selected[: normalized.limit]


def classify_async_operation_for_control(
    operation: ProposalAsyncOperationRecord,
    *,
    as_of: datetime,
) -> AsyncOperationControlStatus:
    if _is_quarantined(operation):
        return "QUARANTINED"
    if operation.status == "SUCCEEDED":
        return "TERMINAL_SUCCEEDED"
    if operation.status == "FAILED":
        if operation.attempt_count >= operation.max_attempts:
            return "RETRY_EXHAUSTED"
        return "TERMINAL_FAILED"
    if operation.status == "PENDING":
        if operation.attempt_count >= operation.max_attempts:
            return "RETRY_EXHAUSTED"
        return "PENDING"
    if _running_lease_has_expired(operation=operation, as_of=as_of):
        if operation.attempt_count >= operation.max_attempts:
            return "RETRY_EXHAUSTED"
        return "RECOVERABLE_STUCK"
    return "LEASED"


def evaluate_async_operation_control(
    *,
    operation: ProposalAsyncOperationRecord,
    action: AsyncOperationControlAction,
    principal: AsyncOperationControlPrincipal,
    as_of: datetime,
    idempotency_key: str,
    reason: str,
) -> AsyncOperationControlDecision:
    control_status = classify_async_operation_for_control(operation, as_of=as_of)
    reason_code = _control_reason_code(
        action=action,
        control_status=control_status,
        principal=principal,
    )
    allowed = reason_code in {
        "ASYNC_CONTROL_DRY_RUN_ALLOWED",
        "ASYNC_CONTROL_RETRY_ALLOWED",
        "ASYNC_CONTROL_QUARANTINE_ALLOWED",
        "ASYNC_CONTROL_ALREADY_QUARANTINED",
        "ASYNC_CONTROL_PAUSE_DRAIN_ALLOWED",
    }
    target_status: ProposalAsyncOperationStatus | None = None
    if allowed and action == "QUARANTINE":
        target_status = "FAILED"

    return AsyncOperationControlDecision(
        allowed=allowed,
        action=action,
        reason_code=reason_code,
        control_status=control_status,
        target_status=target_status,
        schedule_execution=allowed and action == "RETRY",
        payload_mutation_allowed=False,
        audit_event=_build_control_audit_event(
            operation=operation,
            action=action,
            principal=principal,
            as_of=as_of,
            idempotency_key=idempotency_key,
            reason=reason,
            control_status=control_status,
            decision=reason_code,
        ),
        idempotent_noop=reason_code == "ASYNC_CONTROL_ALREADY_QUARANTINED",
    )


def build_quarantined_async_operation(
    *,
    operation: ProposalAsyncOperationRecord,
    decision: AsyncOperationControlDecision,
    finished_at: datetime,
) -> ProposalAsyncOperationRecord:
    if not decision.allowed or decision.action != "QUARANTINE":
        raise ValueError("ASYNC_CONTROL_QUARANTINE_DECISION_REQUIRED")
    if decision.idempotent_noop:
        return cast(ProposalAsyncOperationRecord, operation.model_copy(deep=True))
    return cast(
        ProposalAsyncOperationRecord,
        operation.model_copy(
            deep=True,
            update={
                "status": "FAILED",
                "lease_expires_at": None,
                "finished_at": finished_at,
                "result_json": None,
                "error_json": {
                    "code": ASYNC_OPERATION_QUARANTINED_CODE,
                    "message": ASYNC_OPERATION_QUARANTINED_CODE,
                    "audit_event": decision.audit_event,
                },
            },
        ),
    )


def _control_reason_code(
    *,
    action: AsyncOperationControlAction,
    control_status: AsyncOperationControlStatus,
    principal: AsyncOperationControlPrincipal,
) -> str:
    if not _principal_is_authorized(principal):
        return "ASYNC_CONTROL_NOT_AUTHORIZED"
    if action == "DRY_RUN":
        return "ASYNC_CONTROL_DRY_RUN_ALLOWED"
    if action == "PAUSE_DRAIN":
        return "ASYNC_CONTROL_PAUSE_DRAIN_ALLOWED"
    if action == "RETRY":
        return _retry_reason_code(control_status)
    if action == "QUARANTINE":
        return _quarantine_reason_code(control_status)
    return "ASYNC_CONTROL_UNSUPPORTED_ACTION"


def _retry_reason_code(control_status: AsyncOperationControlStatus) -> str:
    if control_status in {"PENDING", "RECOVERABLE_STUCK"}:
        return "ASYNC_CONTROL_RETRY_ALLOWED"
    if control_status == "LEASED":
        return "ASYNC_CONTROL_RETRY_BLOCKED_BY_ACTIVE_LEASE"
    if control_status == "RETRY_EXHAUSTED":
        return "ASYNC_CONTROL_RETRY_BLOCKED_BY_EXHAUSTED_ATTEMPTS"
    return "ASYNC_CONTROL_RETRY_BLOCKED_BY_TERMINAL_STATE"


def _quarantine_reason_code(control_status: AsyncOperationControlStatus) -> str:
    if control_status == "QUARANTINED":
        return "ASYNC_CONTROL_ALREADY_QUARANTINED"
    if control_status in {"PENDING", "RECOVERABLE_STUCK", "RETRY_EXHAUSTED"}:
        return "ASYNC_CONTROL_QUARANTINE_ALLOWED"
    if control_status == "LEASED":
        return "ASYNC_CONTROL_QUARANTINE_BLOCKED_BY_ACTIVE_LEASE"
    return "ASYNC_CONTROL_QUARANTINE_BLOCKED_BY_TERMINAL_STATE"


def _principal_is_authorized(principal: AsyncOperationControlPrincipal) -> bool:
    return (
        principal.principal_status == "ACTIVE"
        and ASYNC_OPERATION_CONTROL_CAPABILITY in principal.capabilities
        and principal.role.upper() in {"OPERATIONS", "PLATFORM_OPERATOR", "SUPPORT_LEAD"}
    )


def _to_list_item(
    *,
    operation: ProposalAsyncOperationRecord,
    as_of: datetime,
) -> AsyncOperationControlListItem:
    return AsyncOperationControlListItem(
        operation_id=operation.operation_id,
        operation_type=operation.operation_type,
        status=operation.status,
        control_status=classify_async_operation_for_control(operation, as_of=as_of),
        correlation_id=operation.correlation_id,
        proposal_id=operation.proposal_id,
        created_at=operation.created_at,
        started_at=operation.started_at,
        lease_expires_at=operation.lease_expires_at,
        finished_at=operation.finished_at,
        attempt_count=operation.attempt_count,
        max_attempts=operation.max_attempts,
    )


def _running_lease_has_expired(
    *,
    operation: ProposalAsyncOperationRecord,
    as_of: datetime,
) -> bool:
    return (
        operation.status == "RUNNING"
        and operation.finished_at is None
        and operation.lease_expires_at is not None
        and operation.lease_expires_at <= as_of
    )


def _is_quarantined(operation: ProposalAsyncOperationRecord) -> bool:
    return (
        operation.status == "FAILED"
        and isinstance(operation.error_json, dict)
        and operation.error_json.get("code") == ASYNC_OPERATION_QUARANTINED_CODE
    )


def _build_control_audit_event(
    *,
    operation: ProposalAsyncOperationRecord,
    action: AsyncOperationControlAction,
    principal: AsyncOperationControlPrincipal,
    as_of: datetime,
    idempotency_key: str,
    reason: str,
    control_status: AsyncOperationControlStatus,
    decision: str,
) -> dict[str, object]:
    return {
        "event_type": "PROPOSAL_ASYNC_OPERATION_CONTROL_DECISION",
        "operation_ref_hash": _hash_ref("operation", operation.operation_id),
        "correlation_ref_hash": _hash_ref("correlation", operation.correlation_id),
        "proposal_ref_hash": (
            _hash_ref("proposal", operation.proposal_id) if operation.proposal_id else None
        ),
        "actor_ref_hash": _hash_ref("actor", principal.actor_id),
        "service_identity_hash": _hash_ref("service_identity", principal.service_identity),
        "idempotency_key_hash": _hash_ref("idempotency_key", idempotency_key),
        "reason_hash": _hash_ref("reason", reason),
        "action": action,
        "decision": decision,
        "operation_type": operation.operation_type,
        "operation_status": operation.status,
        "control_status": control_status,
        "attempt_count": operation.attempt_count,
        "max_attempts": operation.max_attempts,
        "occurred_at": as_of.isoformat(),
        "payload_mutation_allowed": False,
        "audit_payload_version": "proposal_async_operation_control_decision.v1",
    }


def _hash_ref(kind: str, value: str) -> str:
    return cast(str, hash_canonical_payload({"kind": kind, "value": value}))


__all__ = [
    "ASYNC_OPERATION_CONTROL_CAPABILITY",
    "ASYNC_OPERATION_CONTROL_MAX_LIST_LIMIT",
    "ASYNC_OPERATION_QUARANTINED_CODE",
    "AsyncOperationControlAction",
    "AsyncOperationControlDecision",
    "AsyncOperationControlFilters",
    "AsyncOperationControlListItem",
    "AsyncOperationControlPrincipal",
    "AsyncOperationControlStatus",
    "build_quarantined_async_operation",
    "classify_async_operation_for_control",
    "evaluate_async_operation_control",
    "list_async_operations_for_control",
    "normalize_async_operation_control_filters",
]
