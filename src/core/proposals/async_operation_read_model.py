from dataclasses import dataclass

from src.core.proposals.models import ProposalAsyncOperationRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalAsyncOperationReadModel:
    operation: ProposalAsyncOperationRecord | None


def load_proposal_async_operation_read_model(
    *,
    repository: ProposalRepository,
    operation_id: str,
) -> ProposalAsyncOperationReadModel:
    return ProposalAsyncOperationReadModel(
        operation=repository.get_operation(operation_id=operation_id),
    )


def load_proposal_async_operation_by_correlation_read_model(
    *,
    repository: ProposalRepository,
    correlation_id: str,
) -> ProposalAsyncOperationReadModel:
    return ProposalAsyncOperationReadModel(
        operation=repository.get_operation_by_correlation(correlation_id=correlation_id),
    )
