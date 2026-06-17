from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import cast

from src.core.proposals.async_operation_persistence import (
    persist_async_attempt_started,
    persist_async_operation_failed,
    persist_async_operation_succeeded,
    persist_async_runtime_exception_outcome,
)
from src.core.proposals.async_operation_read_model import load_proposal_async_operation_read_model
from src.core.proposals.async_operations import (
    has_exhausted_async_attempts,
    should_skip_async_operation_run,
)
from src.core.proposals.exceptions import ProposalLifecycleError
from src.core.proposals.models import ProposalAsyncOperationRecord, ProposalCreateResponse
from src.core.proposals.repository import ProposalRepository

ASYNC_OPERATION_LEASE_SECONDS = 60

AsyncOperationExecutor = Callable[[], ProposalCreateResponse]
UtcNow = Callable[[], datetime]


class _AsyncRunOutcome(Enum):
    RETRY = "RETRY"
    TERMINAL = "TERMINAL"


def run_async_operation_until_terminal(
    *,
    repository: ProposalRepository,
    operation_id: str,
    executor: AsyncOperationExecutor,
    utc_now: UtcNow,
) -> None:
    while True:
        read_model = load_proposal_async_operation_read_model(
            repository=repository,
            operation_id=operation_id,
        )
        operation = read_model.operation
        if _should_stop_before_attempt(
            repository=repository,
            operation=operation,
            utc_now=utc_now,
        ):
            return
        operation_for_attempt = cast(ProposalAsyncOperationRecord, operation)

        persist_async_attempt_started(
            repository=repository,
            operation=operation_for_attempt,
            attempt_started_at=utc_now(),
            lease_seconds=ASYNC_OPERATION_LEASE_SECONDS,
        )
        if (
            _run_async_operation_attempt(
                repository=repository,
                operation=operation_for_attempt,
                executor=executor,
                utc_now=utc_now,
            )
            is _AsyncRunOutcome.RETRY
        ):
            continue
        return


def _should_stop_before_attempt(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord | None,
    utc_now: UtcNow,
) -> bool:
    if operation is None or should_skip_async_operation_run(operation):
        return True
    if not has_exhausted_async_attempts(operation):
        return False
    persist_async_operation_failed(
        repository=repository,
        operation=operation,
        code="ProposalLifecycleError",
        message="PROPOSAL_ASYNC_ATTEMPTS_EXHAUSTED",
        finished_at=utc_now(),
    )
    return True


def _run_async_operation_attempt(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    executor: AsyncOperationExecutor,
    utc_now: UtcNow,
) -> _AsyncRunOutcome:
    try:
        response = executor()
    except ProposalLifecycleError as exc:
        _persist_lifecycle_failure(
            repository=repository,
            operation=operation,
            exc=exc,
            finished_at=utc_now(),
        )
        return _AsyncRunOutcome.TERMINAL
    except Exception as exc:
        if persist_async_runtime_exception_outcome(
            repository=repository,
            operation=operation,
            exc=exc,
            finished_at=utc_now(),
        ):
            return _AsyncRunOutcome.RETRY
        return _AsyncRunOutcome.TERMINAL

    persist_async_operation_succeeded(
        repository=repository,
        operation=operation,
        response=response,
        finished_at=utc_now(),
    )
    return _AsyncRunOutcome.TERMINAL


def _persist_lifecycle_failure(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    exc: ProposalLifecycleError,
    finished_at: datetime,
) -> None:
    persist_async_operation_failed(
        repository=repository,
        operation=operation,
        code=type(exc).__name__,
        message=str(exc),
        finished_at=finished_at,
    )
