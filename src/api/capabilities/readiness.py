from src.integrations.lotus_ai import build_lotus_ai_dependency_state
from src.integrations.lotus_core import build_lotus_core_dependency_state
from src.integrations.lotus_performance import build_lotus_performance_dependency_state
from src.integrations.lotus_report import build_lotus_report_dependency_state
from src.integrations.lotus_risk import build_lotus_risk_dependency_state


def build_operational_readiness() -> dict[str, object]:
    dependencies = [
        build_lotus_core_dependency_state(),
        build_lotus_risk_dependency_state(),
        build_lotus_report_dependency_state(),
        build_lotus_ai_dependency_state(),
        build_lotus_performance_dependency_state(),
    ]
    degraded = any(not dependency.operational_ready for dependency in dependencies)
    return {
        "operational_ready": not degraded,
        "degraded": degraded,
        "dependencies": [
            {
                "dependency_key": dependency.key,
                "service_name": dependency.service_name,
                "description": dependency.description,
                "base_url_env": dependency.base_url_env,
                "configured": dependency.configured,
                "operational_ready": dependency.operational_ready,
            }
            for dependency in dependencies
        ],
    }
