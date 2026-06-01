from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from src.core.proposals.async_operation_persistence import persist_async_operation_failed
from src.core.proposals.async_operation_recovery_read_model import (
    load_recoverable_async_operation_read_models,
)
from src.core.proposals.repository import ProposalRepository

ASYNC_RECOVERY_BATCH_SIZE = 50


class AsyncOperationExecutor(Protocol):
    def __call__(self, *, operation_id: str) -> None: ...


def recover_async_operation_batch(
    *,
    repository: ProposalRepository,
    max_operations: int,
    utc_now: Callable[[], datetime],
    execute_create_proposal_async: AsyncOperationExecutor,
    execute_create_version_async: AsyncOperationExecutor,
) -> int:
    recovered = 0
    for read_model in load_recoverable_async_operation_read_models(
        repository=repository,
        as_of=utc_now(),
        limit=max_operations,
    ):
        operation = read_model.operation
        if read_model.operation_kind == "CREATE_PROPOSAL":
            execute_create_proposal_async(operation_id=operation.operation_id)
            recovered += 1
            continue
        if read_model.operation_kind == "CREATE_PROPOSAL_VERSION":
            execute_create_version_async(operation_id=operation.operation_id)
            recovered += 1
            continue
        persist_async_operation_failed(
            repository=repository,
            operation=operation,
            code="ProposalLifecycleError",
            message="PROPOSAL_ASYNC_OPERATION_TYPE_UNSUPPORTED",
            finished_at=utc_now(),
        )
    return recovered


__all__ = ["ASYNC_RECOVERY_BATCH_SIZE", "recover_async_operation_batch"]
