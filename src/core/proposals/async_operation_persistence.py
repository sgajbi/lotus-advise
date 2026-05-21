from datetime import datetime
from typing import cast

from src.core.proposals.async_operations import (
    apply_runtime_exception_outcome,
    begin_async_attempt,
    mark_operation_failed,
    mark_operation_succeeded,
)
from src.core.proposals.models import ProposalAsyncOperationRecord, ProposalCreateResponse
from src.core.proposals.repository import ProposalRepository


def persist_async_attempt_started(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    attempt_started_at: datetime,
    lease_seconds: int,
) -> None:
    begin_async_attempt(
        operation=operation,
        attempt_started_at=attempt_started_at,
        lease_seconds=lease_seconds,
    )
    repository.update_operation(operation)


def persist_async_operation_succeeded(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    response: ProposalCreateResponse,
    finished_at: datetime,
) -> None:
    mark_operation_succeeded(
        operation=operation,
        response=response,
        finished_at=finished_at,
    )
    repository.update_operation(operation)


def persist_async_operation_failed(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    code: str,
    message: str,
    finished_at: datetime,
) -> None:
    mark_operation_failed(
        operation=operation,
        code=code,
        message=message,
        finished_at=finished_at,
    )
    repository.update_operation(operation)


def persist_async_runtime_exception_outcome(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    exc: Exception,
    finished_at: datetime,
) -> bool:
    should_requeue = apply_runtime_exception_outcome(
        operation=operation,
        exc=exc,
        finished_at=finished_at,
    )
    repository.update_operation(operation)
    return cast(bool, should_requeue)
