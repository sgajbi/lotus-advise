from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.proposals.models import ProposalAsyncOperationRecord, ProposalCreateResponse


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
