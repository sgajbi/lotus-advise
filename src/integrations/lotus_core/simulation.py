import sys
from typing import cast

from src.core.models import ProposalResult, ProposalSimulateRequest


class LotusCoreSimulationUnavailableError(Exception):
    pass


def simulate_with_lotus_core(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
) -> ProposalResult:
    main_module = sys.modules.get("src.api.main")
    if main_module is None:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")

    override = getattr(main_module, "simulate_with_lotus_core", None)
    if override is None:
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")

    result = override(
        request=request,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    return cast(ProposalResult, ProposalResult.model_validate(result))
