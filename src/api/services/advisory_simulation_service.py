import uuid
from collections import OrderedDict
from typing import Any, Dict, Optional, cast

from fastapi import HTTPException, status

from src.core.advisory_engine import run_proposal_simulation
from src.core.common.canonical import hash_canonical_payload
from src.core.models import ProposalResult, ProposalSimulateRequest

PROPOSAL_IDEMPOTENCY_CACHE: "OrderedDict[str, Dict[str, object]]" = OrderedDict()
MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE = 1000


def _main_override(name: str) -> Any | None:
    try:
        from src.api import main as main_module
    except ImportError:
        return None
    return getattr(main_module, name, None)


def simulate_proposal_response(
    *,
    request: ProposalSimulateRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
) -> ProposalResult:
    if not request.options.enable_proposal_simulation:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="PROPOSAL_SIMULATION_DISABLED: set options.enable_proposal_simulation=true",
        )

    request_payload = request.model_dump(mode="json")
    request_hash = hash_canonical_payload(request_payload)

    existing = PROPOSAL_IDEMPOTENCY_CACHE.get(idempotency_key)
    if existing and existing["request_hash"] != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
        )
    if existing:
        PROPOSAL_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
        return cast(ProposalResult, ProposalResult.model_validate(existing["response"]))

    run_fn = _main_override("run_proposal_simulation") or run_proposal_simulation
    resolved_correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
    result = run_fn(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=resolved_correlation_id,
    )

    PROPOSAL_IDEMPOTENCY_CACHE[idempotency_key] = {
        "request_hash": request_hash,
        "response": result.model_dump(mode="json"),
    }
    PROPOSAL_IDEMPOTENCY_CACHE.move_to_end(idempotency_key)
    max_cache_size = (
        _main_override("MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE") or MAX_PROPOSAL_IDEMPOTENCY_CACHE_SIZE
    )
    while len(PROPOSAL_IDEMPOTENCY_CACHE) > max_cache_size:
        PROPOSAL_IDEMPOTENCY_CACHE.popitem(last=False)
    return result
