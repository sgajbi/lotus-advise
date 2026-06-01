from datetime import datetime, timezone
from typing import Optional

from src.api.proposals.router import get_proposal_repository
from src.api.services.advisory_simulation_errors import simulation_validation_exception
from src.api.services.advisory_simulation_idempotency import (
    get_replayed_simulation_result,
    save_simulation_idempotency_result,
)
from src.core.advisory.alternatives_normalizer import AlternativesRequestNormalizationError
from src.core.advisory.orchestration import evaluate_advisory_proposal
from src.core.common.canonical import hash_canonical_payload
from src.core.common.idempotency import normalize_required_idempotency_key
from src.core.models import ProposalResult
from src.core.proposals.context import (
    ProposalContextResolutionError,
    ResolvedSimulationContext,
    build_context_resolution_evidence,
    canonicalize_simulation_request_payload,
    resolve_simulation_request,
)
from src.core.proposals.correlation import resolve_correlation_id
from src.core.proposals.models import ProposalSimulationRequest
from src.core.proposals.simulation_gate import (
    ProposalSimulationGateError,
    validate_proposal_simulation_enabled,
)


def simulate_proposal_response(
    *,
    request: ProposalSimulationRequest,
    idempotency_key: str,
    correlation_id: Optional[str],
    resolved_request: ResolvedSimulationContext | None = None,
) -> ProposalResult:
    try:
        idempotency_key = normalize_required_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise simulation_validation_exception(str(exc)) from exc
    resolved_request = resolved_request or resolve_simulation_input(request)

    try:
        validate_proposal_simulation_enabled(request=resolved_request.simulate_request)
    except ProposalSimulationGateError as exc:
        raise simulation_validation_exception(str(exc)) from exc

    request_payload = canonicalize_simulation_request_payload(
        resolved=resolved_request,
    )
    request_hash = hash_canonical_payload(request_payload)
    repository = get_proposal_repository()

    replayed_result = get_replayed_simulation_result(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replayed_result is not None:
        return replayed_result

    resolved_correlation_id = resolve_correlation_id(correlation_id)
    context_resolution = build_context_resolution_evidence(resolved_request)
    try:
        result = evaluate_advisory_proposal(
            request=resolved_request.simulate_request,
            request_hash=request_hash,
            idempotency_key=idempotency_key,
            correlation_id=resolved_correlation_id,
            resolved_as_of=resolved_request.resolved_context.as_of,
            input_mode=resolved_request.input_mode,
            policy_context=context_resolution["advisory_policy_context"],
        )
    except AlternativesRequestNormalizationError as exc:
        raise simulation_validation_exception(f"{exc.reason_code}: {exc}") from exc
    result.explanation["context_resolution"] = context_resolution

    save_simulation_idempotency_result(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        result=result,
        created_at=datetime.now(timezone.utc),
    )
    return result


def resolve_simulation_input(
    request: ProposalSimulationRequest,
) -> ResolvedSimulationContext:
    try:
        return resolve_simulation_request(request)
    except ProposalContextResolutionError as exc:
        raise simulation_validation_exception(str(exc)) from exc
