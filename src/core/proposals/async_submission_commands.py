from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from src.core.proposals.async_operation_read_model import (
    load_proposal_async_operation_by_correlation_read_model,
)
from src.core.proposals.async_operation_submission import (
    persist_create_proposal_async_submission,
    persist_create_version_async_submission,
)
from src.core.proposals.async_operations import (
    AsyncCreateSubmissionStatsTracker,
    build_create_proposal_async_operation,
    build_create_version_async_operation,
)
from src.core.proposals.async_payloads import (
    hash_async_create_submission,
    hash_async_version_submission,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.exceptions import ProposalIdempotencyConflictError
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key
from src.core.proposals.identifiers import new_async_operation_id
from src.core.proposals.models import (
    ProposalAsyncAcceptedResponse,
    ProposalCreateRequest,
    ProposalVersionRequest,
)
from src.core.proposals.projections import to_async_accepted_response
from src.core.proposals.repository import ProposalRepository


def accept_create_proposal_async_submission_command(
    *,
    repository: ProposalRepository,
    payload: ProposalCreateRequest,
    idempotency_key: str,
    correlation_id: str | None,
    max_attempts: int,
    utc_now: Callable[[], datetime],
    submission_stats: AsyncCreateSubmissionStatsTracker,
) -> tuple[ProposalAsyncAcceptedResponse, bool]:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    submission_hash = hash_async_create_submission(payload)
    resolved_correlation_id = resolve_correlation_id(correlation_id)
    operation = build_create_proposal_async_operation(
        operation_id=new_async_operation_id(),
        correlation_id=resolved_correlation_id,
        idempotency_key=idempotency_key,
        payload=payload,
        submission_hash=submission_hash,
        created_at=utc_now(),
        max_attempts=max_attempts,
    )
    submission_result = persist_create_proposal_async_submission(
        repository=repository,
        operation=operation,
        idempotency_key=idempotency_key,
        submission_hash=submission_hash,
    )
    if submission_result.is_conflict:
        submission_stats.record_conflict()
        raise ProposalIdempotencyConflictError(str(submission_result.conflict_message))
    submission_stats.record_acceptance(is_new=submission_result.is_new)
    return to_async_accepted_response(submission_result.operation), submission_result.is_new


def accept_create_version_async_submission_command(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    payload: ProposalVersionRequest,
    correlation_id: str | None,
    max_attempts: int,
    utc_now: Callable[[], datetime],
) -> tuple[ProposalAsyncAcceptedResponse, bool]:
    resolved_correlation_id = resolve_correlation_id(correlation_id)
    submission_hash = hash_async_version_submission(
        proposal_id=proposal_id,
        payload=payload,
    )
    existing_read_model = load_proposal_async_operation_by_correlation_read_model(
        repository=repository,
        correlation_id=resolved_correlation_id,
    )
    operation = build_create_version_async_operation(
        operation_id=new_async_operation_id(),
        proposal_id=proposal_id,
        correlation_id=resolved_correlation_id,
        payload=payload,
        submission_hash=submission_hash,
        created_at=utc_now(),
        max_attempts=max_attempts,
    )
    submission_result = persist_create_version_async_submission(
        repository=repository,
        existing_operation=existing_read_model.operation,
        operation=operation,
        proposal_id=proposal_id,
        submission_hash=submission_hash,
    )
    if submission_result.is_conflict:
        raise ProposalIdempotencyConflictError(str(submission_result.conflict_message))
    return to_async_accepted_response(submission_result.operation), submission_result.is_new


__all__ = [
    "accept_create_proposal_async_submission_command",
    "accept_create_version_async_submission_command",
]
