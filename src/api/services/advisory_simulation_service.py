from typing import Optional

from src.api.proposals.router import get_proposal_repository
from src.api.services.advisory_simulation_evaluation import evaluate_simulation_result
from src.api.services.advisory_simulation_idempotency import (
    get_replayed_simulation_result,
    save_simulation_idempotency_result,
)
from src.api.services.advisory_simulation_validation import (
    normalize_simulation_idempotency_key,
    validate_simulation_request_enabled,
)
from src.api.services.advisory_simulation_validation import (
    resolve_simulation_input as resolve_simulation_input_with_validation,
)
from src.core.models import ProposalResult
from src.core.proposals.context import (
    ResolvedSimulationContext,
    build_simulation_request_hash,
)
from src.core.proposals.models import ProposalSimulationRequest


def simulate_proposal_response(
    *,
    request: ProposalSimulationRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    resolved_request: ResolvedSimulationContext | None = None,
) -> ProposalResult:
    idempotency_key = normalize_simulation_idempotency_key(idempotency_key)
    resolved_request = resolved_request or resolve_simulation_input(request)

    validate_simulation_request_enabled(resolved_request.simulate_request)

    request_hash = build_simulation_request_hash(resolved=resolved_request)
    repository = get_proposal_repository()

    replayed_result = get_replayed_simulation_result(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replayed_result is not None:
        return replayed_result

    result = evaluate_simulation_result(
        resolved_request=resolved_request,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )

    save_simulation_idempotency_result(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        result=result,
    )
    return result


def resolve_simulation_input(
    request: ProposalSimulationRequest,
) -> ResolvedSimulationContext:
    return resolve_simulation_input_with_validation(request)
