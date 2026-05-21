from datetime import datetime
from typing import cast

from src.core.proposals.async_operation_persistence import persist_async_operation_failed
from src.core.proposals.async_payloads import (
    AsyncCreatePayloadResolution,
    AsyncPayloadResolutionFailure,
    AsyncVersionPayloadResolution,
    resolve_async_create_payload,
    resolve_async_version_payload,
)
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateRequest,
    ProposalVersionRequest,
)
from src.core.proposals.repository import ProposalRepository


def resolve_create_async_payload_or_fail(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    fallback_payload: ProposalCreateRequest | None,
    fallback_idempotency_key: str | None,
    failed_at: datetime,
) -> tuple[ProposalCreateRequest, str] | None:
    resolution = resolve_async_create_payload(
        operation=operation,
        fallback_payload=fallback_payload,
        fallback_idempotency_key=fallback_idempotency_key,
    )
    if isinstance(resolution, AsyncPayloadResolutionFailure):
        persist_async_operation_failed(
            repository=repository,
            operation=operation,
            code=resolution.code,
            message=resolution.message,
            finished_at=failed_at,
        )
        return None
    resolved = cast(AsyncCreatePayloadResolution, resolution)
    return resolved.payload, resolved.idempotency_key


def resolve_version_async_payload_or_fail(
    *,
    repository: ProposalRepository,
    operation: ProposalAsyncOperationRecord,
    fallback_proposal_id: str | None,
    fallback_payload: ProposalVersionRequest | None,
    failed_at: datetime,
) -> tuple[str, ProposalVersionRequest] | None:
    resolution = resolve_async_version_payload(
        operation=operation,
        fallback_proposal_id=fallback_proposal_id,
        fallback_payload=fallback_payload,
    )
    if isinstance(resolution, AsyncPayloadResolutionFailure):
        persist_async_operation_failed(
            repository=repository,
            operation=operation,
            code=resolution.code,
            message=resolution.message,
            finished_at=failed_at,
        )
        return None
    resolved = cast(AsyncVersionPayloadResolution, resolution)
    return resolved.proposal_id, resolved.payload
