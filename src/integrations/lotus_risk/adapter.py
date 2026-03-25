from src.integrations.base import IntegrationDependencyState, build_dependency_state


def build_lotus_risk_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_risk",
        service_name="lotus-risk",
        description="Risk analytics and risk-enrichment authority for advisory workflows.",
        base_url_env="LOTUS_RISK_BASE_URL",
    )
