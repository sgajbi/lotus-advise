from dataclasses import dataclass

from src.core.proposals.async_operations import (
    is_matching_create_proposal_async_submission,
    is_matching_create_version_async_submission,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class AsyncOperationSubmissionPersistenceResult:
    operation: ProposalAsyncOperationRecord
    is_new: bool
    conflict_message: str | None = None

    @property
    def is_conflict(self) -> bool:
        return self.conflict_message is not None


def persist_create_proposal_async_submission(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    idempotency_key: str,
    submission_hash: str,
) -> AsyncOperationSubmissionPersistenceResult:
    stored_operation, is_new = repository.create_operation_if_absent_by_idempotency(operation)
    if not is_new and not is_matching_create_proposal_async_submission(
        operation=stored_operation,
        idempotency_key=idempotency_key,
        submission_hash=submission_hash,
    ):
        return AsyncOperationSubmissionPersistenceResult(
            operation=stored_operation,
            is_new=False,
            conflict_message="IDEMPOTENCY_KEY_CONFLICT: async submission hash mismatch",
        )

    return AsyncOperationSubmissionPersistenceResult(
        operation=stored_operation,
        is_new=is_new,
    )


def persist_create_version_async_submission(
    *,
    repository: ProposalRepository,
    existing_operation: ProposalAsyncOperationRecord | None,
    operation: ProposalAsyncOperationRecord,
    proposal_id: str,
    submission_hash: str,
) -> AsyncOperationSubmissionPersistenceResult:
    if existing_operation is not None:
        if not is_matching_create_version_async_submission(
            operation=existing_operation,
            proposal_id=proposal_id,
            submission_hash=submission_hash,
        ):
            return AsyncOperationSubmissionPersistenceResult(
                operation=existing_operation,
                is_new=False,
                conflict_message="CORRELATION_ID_CONFLICT: async version submission mismatch",
            )
        return AsyncOperationSubmissionPersistenceResult(
            operation=existing_operation,
            is_new=False,
        )

    repository.create_operation(operation)
    return AsyncOperationSubmissionPersistenceResult(operation=operation, is_new=True)
