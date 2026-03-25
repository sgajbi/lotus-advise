from src.integrations.base import IntegrationDependencyState, build_dependency_state


def build_lotus_core_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_core",
        service_name="lotus-core",
        description="Canonical portfolio state and portfolio simulation authority.",
        base_url_env="LOTUS_CORE_BASE_URL",
    )
