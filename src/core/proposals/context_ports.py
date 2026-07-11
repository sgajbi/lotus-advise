from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeAlias

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.models import ProposalResolvedContext, ProposalStatefulInput


class ProposalStatefulContextResolutionUnavailableError(Exception):
    authority = "lotus_core"
    degraded_reason = "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"


@dataclass(frozen=True)
class ResolvedStatefulProposalContext:
    simulate_request: ProposalSimulateRequest
    resolved_context: ProposalResolvedContext
    authority: str = "lotus_core"
    lineage: dict[str, Any] | None = None


ProposalStatefulContextResolver: TypeAlias = Callable[
    [ProposalStatefulInput],
    ResolvedStatefulProposalContext | dict[str, Any],
]

_stateful_context_resolver: ProposalStatefulContextResolver | None = None


def configure_proposal_stateful_context_resolver(
    resolver: ProposalStatefulContextResolver | None,
) -> None:
    global _stateful_context_resolver
    _stateful_context_resolver = resolver


def get_proposal_stateful_context_resolver_for_tests() -> ProposalStatefulContextResolver | None:
    return _stateful_context_resolver


def reset_proposal_stateful_context_resolver_for_tests() -> None:
    configure_proposal_stateful_context_resolver(None)


def resolve_proposal_stateful_context(
    stateful_input: ProposalStatefulInput,
) -> ResolvedStatefulProposalContext:
    if _stateful_context_resolver is None:
        raise ProposalStatefulContextResolutionUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE"
        )
    return _coerce_resolved_stateful_context(_stateful_context_resolver(stateful_input))


def _coerce_resolved_stateful_context(
    resolved_payload: object,
) -> ResolvedStatefulProposalContext:
    if isinstance(resolved_payload, ResolvedStatefulProposalContext):
        return resolved_payload
    if not isinstance(resolved_payload, dict):
        raise ProposalStatefulContextResolutionUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
        )
    try:
        simulate_request = ProposalSimulateRequest.model_validate(
            resolved_payload["simulate_request"]
        )
        resolved_context = ProposalResolvedContext.model_validate(
            resolved_payload["resolved_context"]
        )
        lineage_payload = resolved_payload.get("lineage")
        lineage = lineage_payload if isinstance(lineage_payload, dict) else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ProposalStatefulContextResolutionUnavailableError(
            "LOTUS_CORE_STATEFUL_CONTEXT_INVALID"
        ) from exc
    return ResolvedStatefulProposalContext(
        simulate_request=simulate_request,
        resolved_context=resolved_context,
        lineage=lineage,
    )


__all__ = [
    "ProposalStatefulContextResolutionUnavailableError",
    "ProposalStatefulContextResolver",
    "ResolvedStatefulProposalContext",
    "configure_proposal_stateful_context_resolver",
    "get_proposal_stateful_context_resolver_for_tests",
    "reset_proposal_stateful_context_resolver_for_tests",
    "resolve_proposal_stateful_context",
]
