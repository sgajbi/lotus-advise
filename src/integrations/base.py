import os
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class IntegrationDependencyState:
    key: str
    service_name: str
    description: str
    base_url_env: str
    base_url: str | None
    configured: bool
    operational_ready: bool


def runtime_dependency_probing_enabled() -> bool:
    override = os.getenv("LOTUS_DEPENDENCY_RUNTIME_PROBES")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "local").strip().lower() == "production"


def probe_dependency_health(base_url: str) -> bool:
    endpoints = ["/health/ready", "/health"]
    timeout = httpx.Timeout(connect=0.5, read=0.75, write=0.75, pool=0.5)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            for endpoint in endpoints:
                try:
                    response = client.get(f"{base_url.rstrip('/')}{endpoint}")
                except httpx.HTTPError:
                    continue
                if response.status_code == 200:
                    return True
                if endpoint == "/health/ready":
                    return False
    except httpx.HTTPError:
        return False
    return False


def build_dependency_state(
    *,
    key: str,
    service_name: str,
    description: str,
    base_url_env: str,
) -> IntegrationDependencyState:
    base_url = os.getenv(base_url_env, "").strip() or None
    configured = bool(base_url)
    operational_ready = configured
    if configured and base_url and runtime_dependency_probing_enabled():
        operational_ready = probe_dependency_health(base_url)
    return IntegrationDependencyState(
        key=key,
        service_name=service_name,
        description=description,
        base_url_env=base_url_env,
        base_url=base_url,
        configured=configured,
        operational_ready=operational_ready,
    )
