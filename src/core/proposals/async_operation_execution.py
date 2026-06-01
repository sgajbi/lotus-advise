from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from src.core.proposals.async_operation_read_model import load_proposal_async_operation_read_model
from src.core.proposals.async_operation_runner import run_async_operation_until_terminal
from src.core.proposals.async_operations import build_async_replay_lineage
from src.core.proposals.async_payload_resolution import (
    resolve_create_async_payload_or_fail,
    resolve_version_async_payload_or_fail,
)
from src.core.proposals.models import (
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalVersionRequest,
)
from src.core.proposals.repository import ProposalRepository


class CreateProposalExecutor(Protocol):
    def __call__(
        self,
        *,
        payload: ProposalCreateRequest,
        idempotency_key: str,
        correlation_id: str | None,
        replay_lineage: dict[str, Any] | None,
    ) -> ProposalCreateResponse: ...


class CreateVersionExecutor(Protocol):
    def __call__(
        self,
        *,
        proposal_id: str,
        payload: ProposalVersionRequest,
        correlation_id: str | None,
        replay_lineage: dict[str, Any] | None,
    ) -> ProposalCreateResponse: ...


def execute_create_proposal_async_operation(
    *,
    repository: ProposalRepository,
    operation_id: str,
    fallback_payload: ProposalCreateRequest | None,
    fallback_idempotency_key: str | None,
    fallback_correlation_id: str | None,
    utc_now: Callable[[], datetime],
    create_proposal: CreateProposalExecutor,
) -> None:
    read_model = load_proposal_async_operation_read_model(
        repository=repository,
        operation_id=operation_id,
    )
    if read_model.operation is None:
        return
    operation = read_model.operation
    recovered_payload = resolve_create_async_payload_or_fail(
        repository=repository,
        operation=operation,
        fallback_payload=fallback_payload,
        fallback_idempotency_key=fallback_idempotency_key,
        failed_at=utc_now(),
    )
    if recovered_payload is None:
        return
    request_payload, resolved_idempotency_key = recovered_payload
    run_async_operation_until_terminal(
        repository=repository,
        operation_id=operation_id,
        executor=lambda: create_proposal(
            payload=request_payload,
            idempotency_key=resolved_idempotency_key,
            correlation_id=fallback_correlation_id or operation.correlation_id,
            replay_lineage=build_async_replay_lineage(operation),
        ),
        utc_now=utc_now,
    )


def execute_create_version_async_operation(
    *,
    repository: ProposalRepository,
    operation_id: str,
    fallback_proposal_id: str | None,
    fallback_payload: ProposalVersionRequest | None,
    fallback_correlation_id: str | None,
    utc_now: Callable[[], datetime],
    create_version: CreateVersionExecutor,
) -> None:
    read_model = load_proposal_async_operation_read_model(
        repository=repository,
        operation_id=operation_id,
    )
    if read_model.operation is None:
        return
    operation = read_model.operation
    recovered_payload = resolve_version_async_payload_or_fail(
        repository=repository,
        operation=operation,
        fallback_proposal_id=fallback_proposal_id,
        fallback_payload=fallback_payload,
        failed_at=utc_now(),
    )
    if recovered_payload is None:
        return
    resolved_proposal_id, request_payload = recovered_payload
    run_async_operation_until_terminal(
        repository=repository,
        operation_id=operation_id,
        executor=lambda: create_version(
            proposal_id=resolved_proposal_id,
            payload=request_payload,
            correlation_id=fallback_correlation_id or operation.correlation_id,
            replay_lineage=build_async_replay_lineage(operation),
        ),
        utc_now=utc_now,
    )


__all__ = [
    "execute_create_proposal_async_operation",
    "execute_create_version_async_operation",
]
