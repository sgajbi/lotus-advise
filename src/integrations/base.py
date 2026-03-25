import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationDependencyState:
    key: str
    service_name: str
    description: str
    base_url_env: str
    base_url: str | None
    configured: bool
    operational_ready: bool


def build_dependency_state(
    *,
    key: str,
    service_name: str,
    description: str,
    base_url_env: str,
) -> IntegrationDependencyState:
    base_url = os.getenv(base_url_env, "").strip() or None
    configured = bool(base_url)
    return IntegrationDependencyState(
        key=key,
        service_name=service_name,
        description=description,
        base_url_env=base_url_env,
        base_url=base_url,
        configured=configured,
        operational_ready=configured,
    )
