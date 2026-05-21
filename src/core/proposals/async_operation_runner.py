from collections.abc import Callable
from datetime import datetime
from typing import Any

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
from src.core.proposals.repository import ProposalRepository

ASYNC_OPERATION_LEASE_SECONDS = 60

AsyncOperationExecutor = Callable[[], Any]
UtcNow = Callable[[], datetime]


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
        if should_skip_async_operation_run(operation):
            return
        assert operation is not None
        if has_exhausted_async_attempts(operation):
            persist_async_operation_failed(
                repository=repository,
                operation=operation,
                code="ProposalLifecycleError",
                message="PROPOSAL_ASYNC_ATTEMPTS_EXHAUSTED",
                finished_at=utc_now(),
            )
            return

        persist_async_attempt_started(
            repository=repository,
            operation=operation,
            attempt_started_at=utc_now(),
            lease_seconds=ASYNC_OPERATION_LEASE_SECONDS,
        )
        try:
            response = executor()
        except ProposalLifecycleError as exc:
            persist_async_operation_failed(
                repository=repository,
                operation=operation,
                code=type(exc).__name__,
                message=str(exc),
                finished_at=utc_now(),
            )
            return
        except Exception as exc:
            if persist_async_runtime_exception_outcome(
                repository=repository,
                operation=operation,
                exc=exc,
                finished_at=utc_now(),
            ):
                continue
            return

        persist_async_operation_succeeded(
            repository=repository,
            operation=operation,
            response=response,
            finished_at=utc_now(),
        )
        return
