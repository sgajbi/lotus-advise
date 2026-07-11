from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeAlias

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.workspace.input_models import WorkspaceResolvedContext, WorkspaceStatefulInput


class LotusCoreContextResolutionError(Exception):
    pass


@dataclass(frozen=True)
class LotusCoreResolvedAdvisoryContext:
    simulate_request: ProposalSimulateRequest
    resolved_context: WorkspaceResolvedContext


LotusCoreAdvisoryContextResolver: TypeAlias = Callable[
    [WorkspaceStatefulInput],
    LotusCoreResolvedAdvisoryContext | dict[str, Any],
]

_context_resolver: LotusCoreAdvisoryContextResolver | None = None


def configure_lotus_core_advisory_context_resolver(
    resolver: LotusCoreAdvisoryContextResolver | None,
) -> None:
    global _context_resolver
    _context_resolver = resolver


def get_lotus_core_advisory_context_resolver_for_tests() -> LotusCoreAdvisoryContextResolver | None:
    return _context_resolver


def reset_lotus_core_advisory_context_resolver_for_tests() -> None:
    configure_lotus_core_advisory_context_resolver(None)


def resolve_lotus_core_advisory_context(
    stateful_input: WorkspaceStatefulInput,
) -> LotusCoreResolvedAdvisoryContext:
    if _context_resolver is None:
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")

    resolved_payload = _context_resolver(stateful_input)
    return _coerce_resolved_advisory_context(resolved_payload)


def _coerce_resolved_advisory_context(
    resolved_payload: object,
) -> LotusCoreResolvedAdvisoryContext:
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
