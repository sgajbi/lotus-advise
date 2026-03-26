import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict, Optional, cast

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.proposals.router import get_proposal_repository
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.core.proposals.models import ProposalSimulationIdempotencyRecord

PROPOSAL_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE = 1000


def simulate_proposal_response(
    *,
    request: ProposalSimulateRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
) -> ProposalResult:
    if not request.options.enable_proposal_simulation:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true",
        )

    request_payload = request.model_dump(mode="json")
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
    result = evaluate_advisory_proposal(
        request=request,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=resolved_correlation_id,
    )

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
