from __future__ import annotations

from src.api.services.advisory_simulation_errors import simulation_validation_exception
from src.core.common.idempotency import normalize_required_idempotency_key
from src.core.models import ProposalSimulateRequest
from src.core.proposals.context import (
    ProposalContextResolutionError,
    ResolvedSimulationContext,
    resolve_simulation_request,
)
from src.core.proposals.models import ProposalSimulationRequest
from src.core.proposals.simulation_gate import (
    ProposalSimulationGateError,
    validate_proposal_simulation_enabled,
)


def normalize_simulation_idempotency_key(idempotency_key: str) -> str:
    try:
        return normalize_required_idempotency_key(idempotency_key)
    except ValueError as exc:
        raise simulation_validation_exception(str(exc)) from exc


def validate_simulation_request_enabled(request: ProposalSimulateRequest) -> None:
    try:
        validate_proposal_simulation_enabled(request=request)
    except ProposalSimulationGateError as exc:
        raise simulation_validation_exception(str(exc)) from exc


def resolve_simulation_input(
    request: ProposalSimulationRequest,
) -> ResolvedSimulationContext:
    try:
        return resolve_simulation_request(request)
    except ProposalContextResolutionError as exc:
        raise simulation_validation_exception(str(exc)) from exc
