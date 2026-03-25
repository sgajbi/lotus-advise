import sys
from dataclasses import dataclass

from src.core.models import ProposalSimulateRequest
from src.core.workspace.models import WorkspaceResolvedContext, WorkspaceStatefulInput


class LotusCoreContextResolutionError(Exception):
    pass


@dataclass(frozen=True)
class LotusCoreResolvedAdvisoryContext:
    simulate_request: ProposalSimulateRequest
    resolved_context: WorkspaceResolvedContext


def resolve_lotus_core_advisory_context(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext:
    main_module = sys.modules.get("src.api.main")
    if main_module is None:
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")

    override = getattr(main_module, "resolve_lotus_core_advisory_context", None)
    if override is None:
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")

    resolved_payload = override(stateful_input)
    if isinstance(resolved_payload, LotusCoreResolvedAdvisoryContext):
        return resolved_payload

    if not isinstance(resolved_payload, dict):
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_INVALID")

    try:
        simulate_request = ProposalSimulateRequest.model_validate(
            resolved_payload["simulate_request"]
        )
        resolved_context = WorkspaceResolvedContext.model_validate(
            resolved_payload["resolved_context"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_INVALID") from exc

    return LotusCoreResolvedAdvisoryContext(
        simulate_request=simulate_request,
        resolved_context=resolved_context,
    )
