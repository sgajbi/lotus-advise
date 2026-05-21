from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Literal

from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalVersionRequest,
)

RecoverableAsyncOperationKind = Literal["CREATE_PROPOSAL", "CREATE_PROPOSAL_VERSION"]
ASYNC_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED"}


@dataclass(frozen=True)
class AsyncCreateSubmissionStats:
    accepted_new: int
    accepted_replayed: int
    conflicts: int


class AsyncCreateSubmissionStatsTracker:
    def __init__(self) -> None:
        self._lock = RLock()
        self._accepted_new = 0
        self._accepted_replayed = 0
        self._conflicts = 0

    def record_acceptance(self, *, is_new: bool) -> None:
        with self._lock:
            if is_new:
                self._accepted_new += 1
                return
            self._accepted_replayed += 1

    def record_conflict(self) -> None:
        with self._lock:
            self._conflicts += 1

    def snapshot(self) -> AsyncCreateSubmissionStats:
        with self._lock:
            return AsyncCreateSubmissionStats(
                accepted_new=self._accepted_new,
                accepted_replayed=self._accepted_replayed,
                conflicts=self._conflicts,
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


def is_matching_create_proposal_async_submission(
    *,
    operation: ProposalAsyncOperationRecord,
    idempotency_key: str,
    submission_hash: str | None,
) -> bool:
    return (
        operation.operation_type == "CREATE_PROPOSAL"
        and operation.idempotency_key == idempotency_key
        and submission_hash is not None
        and operation.payload_json.get("submission_hash") == submission_hash
    )


def is_matching_create_version_async_submission(
    *,
    operation: ProposalAsyncOperationRecord,
    proposal_id: str,
    submission_hash: str | None,
) -> bool:
    return (
        operation.operation_type == "CREATE_PROPOSAL_VERSION"
        and operation.proposal_id == proposal_id
        and submission_hash is not None
        and operation.payload_json.get("submission_hash") == submission_hash
    )


def resolve_recoverable_async_operation_kind(
    operation: ProposalAsyncOperationRecord,
) -> RecoverableAsyncOperationKind | None:
    if operation.operation_type == "CREATE_PROPOSAL":
        return "CREATE_PROPOSAL"
    if operation.operation_type == "CREATE_PROPOSAL_VERSION":
        return "CREATE_PROPOSAL_VERSION"
    return None


def should_skip_async_operation_run(operation: ProposalAsyncOperationRecord | None) -> bool:
    return operation is None or operation.status in ASYNC_TERMINAL_STATUSES


def has_exhausted_async_attempts(operation: ProposalAsyncOperationRecord) -> bool:
    return operation.attempt_count >= operation.max_attempts


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


def extract_async_result_version_no(operation: ProposalAsyncOperationRecord) -> int | None:
    if operation.result_json is None:
        return None
    version_payload = operation.result_json.get("version")
    if not isinstance(version_payload, dict):
        return None
    version_no = version_payload.get("version_no")
    return version_no if isinstance(version_no, int) else None
