from __future__ import annotations

from datetime import datetime, timezone
from typing import cast

from src.api.services.advisory_simulation_errors import (
    simulation_idempotency_conflict_exception,
    simulation_idempotency_store_unavailable_exception,
)
from src.core.models import ProposalResult
from src.core.proposals.models import ProposalSimulationIdempotencyRecord
from src.core.proposals.repository import ProposalRepository


def get_replayed_simulation_result(
    *,
    repository: ProposalRepository,
    idempotency_key: str,
    request_hash: str,
) -> ProposalResult | None:
    existing = repository.get_simulation_idempotency(idempotency_key=idempotency_key)
    if existing is not None and existing.request_hash != request_hash:
        raise simulation_idempotency_conflict_exception()
    if existing is None:
        return None
    return cast(ProposalResult, ProposalResult.model_validate(existing.response_json))


def save_simulation_idempotency_result(
    *,
    repository: ProposalRepository,
    idempotency_key: str,
    request_hash: str,
    result: ProposalResult,
    created_at: datetime | None = None,
) -> None:
    try:
        repository.save_simulation_idempotency(
            ProposalSimulationIdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=result.model_dump(mode="json"),
                created_at=created_at or datetime.now(timezone.utc),
            )
        )
    except (RuntimeError, ValueError, TypeError, ConnectionError) as exc:
        raise simulation_idempotency_store_unavailable_exception() from exc
