import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, Optional, cast

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.proposals.router import get_proposal_repository
from src.core.advisory.alternatives_normalizer import AlternativesRequestNormalizationError
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult
from src.core.proposals.context import (
    ProposalContextResolutionError,
    ResolvedSimulationContext,
    build_context_resolution_evidence,
    canonicalize_simulation_request_payload,
    resolve_simulation_request,
)
from src.core.proposals.models import (
    ProposalSimulationIdempotencyRecord,
    ProposalSimulationRequest,
)

PROPOSAL_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE = 1000


def simulate_proposal_response(
    *,
    request: ProposalSimulationRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    resolved_request: ResolvedSimulationContext | None = None,
) -> ProposalResult:
    resolved_request = resolved_request or resolve_simulation_input(request)

    if not resolved_request.simulate_request.options.enable_proposal_simulation:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true",
        )

    request_payload = canonicalize_simulation_request_payload(
        resolved=resolved_request,
    )
    request_hash = hash_canonical_payload(request_payload)
    repository = get_proposal_repository()

    existing = repository.get_simulation_idempotency(idempotency_key=idempotency_key)
    if existing is not None and existing.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
        )
    if existing is not None:
        return cast(ProposalResult, ProposalResult.model_validate(existing.response_json))

    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    context_resolution = build_context_resolution_evidence(resolved_request)
    try:
        result = evaluate_advisory_proposal(
            request=resolved_request.simulate_request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=resolved_correlation_id,
            resolved_as_of=resolved_request.resolved_context.as_of,
            policy_context=context_resolution["advisory_policy_context"],
        )
    except AlternativesRequestNormalizationError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=f"{exc.reason_code}: {exc}",
        ) from exc
    result.explanation["context_resolution"] = context_resolution

    try:
        repository.save_simulation_idempotency(
            ProposalSimulationIdempotencyRecord(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=result.model_dump(mode="json"),
                created_at=datetime.now(timezone.utc),
            )
        )
    except (RuntimeError, ValueError, TypeError, ConnectionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PROPOSAL_IDEMPOTENCY_STORE_WRITE_FAILED",
        ) from exc
    return result


def resolve_simulation_input(
    request: ProposalSimulationRequest,
) -> ResolvedSimulationContext:
    try:
        return resolve_simulation_request(request)
    except ProposalContextResolutionError as exc:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE, detail=str(exc)) from exc
