from src.integrations.base import IntegrationDependencyState, build_dependency_state


def build_lotus_ai_dependency_state() -> IntegrationDependencyState:
    return build_dependency_state(
        key="lotus_ai",
        service_name="lotus-ai",
        description="Governed AI runtime for advisor-assistive Lotus workflows.",
        base_url_env="LOTUS_AI_BASE_URL",
    )
