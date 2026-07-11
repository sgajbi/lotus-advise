from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposal_result_models import ProposalResult

_NON_PRODUCTION_FALLBACK_ENVIRONMENTS = {"local", "dev", "development", "test", "ci"}
_LOTUS_CORE_SIMULATION_UNAVAILABLE = "LOTUS_CORE_SIMULATION_UNAVAILABLE"
_LOTUS_RISK_DEPENDENCY_UNAVAILABLE = "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
_LOTUS_RISK_ENRICHMENT_UNAVAILABLE = "LOTUS_RISK_ENRICHMENT_UNAVAILABLE"


class AdvisorySimulationUnavailableError(Exception):
    authority = "lotus_core"
    degraded_reason = _LOTUS_CORE_SIMULATION_UNAVAILABLE

    def __init__(self, detail: str, *, status_code: int | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AdvisoryRiskEnrichmentUnavailableError(Exception):
    authority = "lotus_risk"
    degraded_reason = _LOTUS_RISK_ENRICHMENT_UNAVAILABLE


@dataclass(frozen=True)
class AdvisoryProviderDependencyState:
    configured: bool
    degraded_reason: str | None = None


@dataclass(frozen=True)
class AdvisorySimulationFallbackPolicy:
    requested: bool
    permitted: bool
    enabled: bool


AdvisorySimulationProvider: TypeAlias = Callable[
    [
        ProposalSimulateRequest,
        str,
        str | None,
        str,
        dict[str, object] | None,
    ],
    ProposalResult,
]
AdvisoryRiskEnrichmentProvider: TypeAlias = Callable[
    [
        ProposalSimulateRequest,
        ProposalResult,
        str,
        str | None,
        str | None,
    ],
    ProposalResult,
]
AdvisoryRiskDependencyStateProvider: TypeAlias = Callable[[], AdvisoryProviderDependencyState]
AdvisorySimulationFallbackPolicyProvider: TypeAlias = Callable[
    [],
    AdvisorySimulationFallbackPolicy,
]

_simulation_provider: AdvisorySimulationProvider | None = None
_risk_enrichment_provider: AdvisoryRiskEnrichmentProvider | None = None
_risk_dependency_state_provider: AdvisoryRiskDependencyStateProvider | None = None
_simulation_fallback_policy_provider: AdvisorySimulationFallbackPolicyProvider | None = None


def configure_advisory_simulation_provider(
    provider: AdvisorySimulationProvider | None,
) -> None:
    global _simulation_provider
    _simulation_provider = provider


def configure_advisory_risk_enrichment_provider(
    provider: AdvisoryRiskEnrichmentProvider | None,
) -> None:
    global _risk_enrichment_provider
    _risk_enrichment_provider = provider


def configure_advisory_risk_dependency_state_provider(
    provider: AdvisoryRiskDependencyStateProvider | None,
) -> None:
    global _risk_dependency_state_provider
    _risk_dependency_state_provider = provider


def configure_advisory_simulation_fallback_policy_provider(
    provider: AdvisorySimulationFallbackPolicyProvider | None,
) -> None:
    global _simulation_fallback_policy_provider
    _simulation_fallback_policy_provider = provider


def reset_advisory_provider_ports_for_tests() -> None:
    configure_advisory_simulation_provider(None)
    configure_advisory_risk_enrichment_provider(None)
    configure_advisory_risk_dependency_state_provider(None)
    configure_advisory_simulation_fallback_policy_provider(None)


def get_advisory_simulation_provider_for_tests() -> AdvisorySimulationProvider | None:
    return _simulation_provider


def get_advisory_risk_enrichment_provider_for_tests() -> AdvisoryRiskEnrichmentProvider | None:
    return _risk_enrichment_provider


def simulate_with_advisory_simulation_provider(
    *,
    request: ProposalSimulateRequest,
    request_hash: str,
    idempotency_key: str | None,
    correlation_id: str,
    policy_context: dict[str, object] | None = None,
) -> ProposalResult:
    if _simulation_provider is None:
        raise AdvisorySimulationUnavailableError(_LOTUS_CORE_SIMULATION_UNAVAILABLE)
    return _simulation_provider(
        request,
        request_hash,
        idempotency_key,
        correlation_id,
        policy_context,
    )


def enrich_with_advisory_risk_provider(
    *,
    request: ProposalSimulateRequest,
    proposal_result: ProposalResult,
    correlation_id: str,
    resolved_as_of: str | None = None,
    input_mode: str | None = None,
) -> ProposalResult:
    if _risk_enrichment_provider is None:
        raise AdvisoryRiskEnrichmentUnavailableError(_LOTUS_RISK_ENRICHMENT_UNAVAILABLE)
    return _risk_enrichment_provider(
        request,
        proposal_result,
        correlation_id,
        resolved_as_of,
        input_mode,
    )


def build_advisory_risk_dependency_state() -> AdvisoryProviderDependencyState:
    if _risk_dependency_state_provider is None:
        return AdvisoryProviderDependencyState(
            configured=False,
            degraded_reason=_LOTUS_RISK_DEPENDENCY_UNAVAILABLE,
        )
    return _risk_dependency_state_provider()


def resolve_advisory_simulation_fallback_policy() -> AdvisorySimulationFallbackPolicy:
    if _simulation_fallback_policy_provider is not None:
        return _simulation_fallback_policy_provider()
    requested = _truthy_env("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK")
    permitted = _environment_allows_local_fallback()
    return AdvisorySimulationFallbackPolicy(
        requested=requested,
        permitted=permitted,
        enabled=requested and permitted,
    )


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _environment_allows_local_fallback() -> bool:
    return (
        os.getenv("ENVIRONMENT", "local").strip().lower() in _NON_PRODUCTION_FALLBACK_ENVIRONMENTS
    )


__all__ = [
    "AdvisoryProviderDependencyState",
    "AdvisoryRiskEnrichmentProvider",
    "AdvisoryRiskEnrichmentUnavailableError",
    "AdvisorySimulationFallbackPolicy",
    "AdvisorySimulationFallbackPolicyProvider",
    "AdvisorySimulationProvider",
    "AdvisorySimulationUnavailableError",
    "build_advisory_risk_dependency_state",
    "configure_advisory_risk_dependency_state_provider",
    "configure_advisory_risk_enrichment_provider",
    "configure_advisory_simulation_fallback_policy_provider",
    "configure_advisory_simulation_provider",
    "enrich_with_advisory_risk_provider",
    "get_advisory_risk_enrichment_provider_for_tests",
    "get_advisory_simulation_provider_for_tests",
    "reset_advisory_provider_ports_for_tests",
    "resolve_advisory_simulation_fallback_policy",
    "simulate_with_advisory_simulation_provider",
]
