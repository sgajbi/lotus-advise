from src.integrations.base import IntegrationDependencyState, build_dependency_state


def build_lotus_performance_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_performance",
        service_name="lotus-performance",
        description="Performance analytics context for advisory workflows when enabled.",
        base_url_env="LOTUS_PERFORMANCE_BASE_URL",
    )
