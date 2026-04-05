import os

from src.integrations.base import IntegrationDependencyState, build_dependency_state

CONTROLLED_LOCAL_SIMULATION_FALLBACK = "CONTROLLED_LOCAL_SIMULATION_FALLBACK"
_NON_PRODUCTION_FALLBACK_ENVIRONMENTS = {"local", "dev", "development", "test", "ci"}


def build_lotus_core_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_core",
        service_name="lotus-core",
        description="Canonical portfolio state and portfolio simulation authority.",
        base_url_env="LOTUS_CORE_BASE_URL",
    )


def lotus_core_local_fallback_enabled() -> bool:
    return lotus_core_local_fallback_requested() and lotus_core_local_fallback_permitted()


def lotus_core_local_fallback_requested() -> bool:
    return os.getenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def lotus_core_local_fallback_permitted() -> bool:
    return (
        os.getenv("ENVIRONMENT", "local").strip().lower() in _NON_PRODUCTION_FALLBACK_ENVIRONMENTS
    )


def lotus_core_fallback_mode() -> str:
    return CONTROLLED_LOCAL_SIMULATION_FALLBACK if lotus_core_local_fallback_enabled() else "NONE"
