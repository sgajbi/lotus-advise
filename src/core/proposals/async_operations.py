from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalVersionRequest,
)


def build_create_proposal_async_operation(
    *,
    operation_id: str,
    correlation_id: str,
    idempotency_key: str,
    payload: ProposalCreateRequest,
    submission_hash: str,
    created_at: datetime,
    max_attempts: int,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        proposal_id=None,
        created_by=payload.created_by,
        created_at=created_at,
        payload_json={
            "payload": payload.model_dump(mode="json"),
            "idempotency_key": idempotency_key,
            "submission_hash": submission_hash,
        },
        attempt_count=0,
        max_attempts=max_attempts,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )


def build_create_version_async_operation(
    *,
    operation_id: str,
    proposal_id: str,
    correlation_id: str,
    payload: ProposalVersionRequest,
    submission_hash: str,
    created_at: datetime,
    max_attempts: int,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="CREATE_PROPOSAL_VERSION",
        status="PENDING",
        correlation_id=correlation_id,
        idempotency_key=None,
        proposal_id=proposal_id,
        created_by=payload.created_by,
        created_at=created_at,
        payload_json={
            "proposal_id": proposal_id,
            "payload": payload.model_dump(mode="json"),
            "submission_hash": submission_hash,
        },
        attempt_count=0,
        max_attempts=max_attempts,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )


def begin_async_attempt(
    *,
    operation: ProposalAsyncOperationRecord,
    attempt_started_at: datetime,
    lease_seconds: int,
) -> None:
    operation.status = "RUNNING"
    operation.attempt_count += 1
    operation.started_at = attempt_started_at
    operation.lease_expires_at = attempt_started_at + timedelta(seconds=lease_seconds)
    operation.finished_at = None
    operation.result_json = None
    operation.error_json = None


def mark_operation_succeeded(
    *,
    operation: ProposalAsyncOperationRecord,
    response: ProposalCreateResponse,
    finished_at: datetime,
) -> None:
    operation.status = "SUCCEEDED"
    operation.proposal_id = response.proposal.proposal_id
    operation.result_json = response.model_dump(mode="json", warnings=False)
    operation.error_json = None
    operation.lease_expires_at = None
    operation.finished_at = finished_at


def mark_operation_failed(
    *,
    operation: ProposalAsyncOperationRecord,
    code: str,
    message: str,
    finished_at: datetime,
) -> None:
    operation.status = "FAILED"
    operation.result_json = None
    operation.error_json = {"code": code, "message": message}
    operation.lease_expires_at = None
    operation.finished_at = finished_at


def apply_runtime_exception_outcome(
    *,
    operation: ProposalAsyncOperationRecord,
    exc: Exception,
    finished_at: datetime,
) -> bool:
    operation.result_json = None
    operation.lease_expires_at = None
    operation.error_json = {
        "code": type(exc).__name__,
        "message": str(exc) or type(exc).__name__,
    }
    if operation.attempt_count < operation.max_attempts:
        operation.status = "PENDING"
        operation.finished_at = None
        return True

    operation.status = "FAILED"
    operation.finished_at = finished_at
    return False


def build_async_replay_lineage(operation: ProposalAsyncOperationRecord) -> dict[str, Any]:
    return {
        "async_operation_id": operation.operation_id,
        "async_operation_type": operation.operation_type,
        "correlation_id": operation.correlation_id,
        "idempotency_key": operation.idempotency_key,
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
