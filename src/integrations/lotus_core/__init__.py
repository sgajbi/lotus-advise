from __future__ import annotations

from importlib import import_module
from typing import Final

_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "CONTROLLED_LOCAL_SIMULATION_FALLBACK": (
        "src.integrations.lotus_core.adapter",
        "CONTROLLED_LOCAL_SIMULATION_FALLBACK",
    ),
    "LotusCoreContextResolutionError": (
        "src.integrations.lotus_core.context_resolution",
        "LotusCoreContextResolutionError",
    ),
    "LotusCoreAdvisoryContextResolver": (
        "src.integrations.lotus_core.context_resolution",
        "LotusCoreAdvisoryContextResolver",
    ),
    "LotusCoreResolvedAdvisoryContext": (
        "src.integrations.lotus_core.context_resolution",
        "LotusCoreResolvedAdvisoryContext",
    ),
    "LotusCoreSimulationUnavailableError": (
        "src.integrations.lotus_core.simulation",
        "LotusCoreSimulationUnavailableError",
    ),
    "build_lotus_core_dependency_state": (
        "src.integrations.lotus_core.adapter",
        "build_lotus_core_dependency_state",
    ),
    "configure_lotus_core_advisory_context_resolver": (
        "src.integrations.lotus_core.context_resolution",
        "configure_lotus_core_advisory_context_resolver",
    ),
    "get_lotus_core_advisory_context_resolver_for_tests": (
        "src.integrations.lotus_core.context_resolution",
        "get_lotus_core_advisory_context_resolver_for_tests",
    ),
    "lotus_core_fallback_mode": (
        "src.integrations.lotus_core.adapter",
        "lotus_core_fallback_mode",
    ),
    "lotus_core_local_fallback_enabled": (
        "src.integrations.lotus_core.adapter",
        "lotus_core_local_fallback_enabled",
    ),
    "lotus_core_local_fallback_permitted": (
        "src.integrations.lotus_core.adapter",
        "lotus_core_local_fallback_permitted",
    ),
    "lotus_core_local_fallback_requested": (
        "src.integrations.lotus_core.adapter",
        "lotus_core_local_fallback_requested",
    ),
    "resolve_lotus_core_advisory_context": (
        "src.integrations.lotus_core.context_resolution",
        "resolve_lotus_core_advisory_context",
    ),
    "reset_lotus_core_advisory_context_resolver_for_tests": (
        "src.integrations.lotus_core.context_resolution",
        "reset_lotus_core_advisory_context_resolver_for_tests",
    ),
    "simulate_with_lotus_core": (
        "src.integrations.lotus_core.simulation",
        "simulate_with_lotus_core",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value
