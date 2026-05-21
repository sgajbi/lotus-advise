from dataclasses import dataclass
from datetime import datetime

from src.core.proposals.async_operations import (
    RecoverableAsyncOperationKind,
    resolve_recoverable_async_operation_kind,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class RecoverableAsyncOperationReadModel:
    operation: ProposalAsyncOperationRecord
    operation_kind: RecoverableAsyncOperationKind | None


def load_recoverable_async_operation_read_models(
    *,
    repository: ProposalRepository,
    as_of: datetime,
    limit: int | None = None,
) -> list[RecoverableAsyncOperationReadModel]:
    return [
        RecoverableAsyncOperationReadModel(
            operation=operation,
            operation_kind=resolve_recoverable_async_operation_kind(operation),
        )
        for operation in repository.list_recoverable_operations(as_of=as_of, limit=limit)
    ]
