import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

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
    runtime_probe_enabled: bool
    readiness_basis: str
    degraded_reason: str | None


def runtime_dependency_probing_enabled() -> bool:
    override = os.getenv("LOTUS_DEPENDENCY_RUNTIME_PROBES")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return os.getenv("ENVIRONMENT", "local").strip().lower() == "production"


def probe_dependency_health(base_url: str) -> bool:
    if not _is_http_probe_base_url(base_url):
        return False
    endpoints = ["/health/ready", "/health"]
    timeout = httpx.Timeout(connect=0.5, read=0.75, write=0.75, pool=0.5)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
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


def _is_http_probe_base_url(base_url: str) -> bool:
    return sanitized_http_base_url(base_url) is not None


def sanitized_http_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    trimmed = base_url.strip().rstrip("/")
    if not trimmed:
        return None
    split = urlsplit(base_url.strip())
    if split.scheme not in {"http", "https"} or split.hostname is None:
        return None
    try:
        port = split.port
    except ValueError:
        return None
    netloc = split.hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((split.scheme, netloc, split.path.rstrip("/"), "", ""))


def public_dependency_base_url(base_url: str | None) -> str | None:
    if base_url is None:
        return None
    trimmed = base_url.strip().rstrip("/")
    if not trimmed:
        return None
    split = urlsplit(trimmed)
    if not split.scheme or not split.netloc:
        return trimmed
    return sanitized_http_base_url(trimmed)


def build_dependency_state(
    *,
    key: str,
    service_name: str,
    description: str,
    base_url_env: str,
) -> IntegrationDependencyState:
    configured_base_url = os.getenv(base_url_env, "").strip() or None
    public_base_url = public_dependency_base_url(configured_base_url)
    configured = bool(configured_base_url)
    probe_enabled = configured and runtime_dependency_probing_enabled()
    reason_key = key.upper().replace("-", "_")
    degraded_reason: str | None = f"{reason_key}_DEPENDENCY_UNAVAILABLE"

    if not configured:
        operational_ready = False
        readiness_basis = "not_configured"
    elif not probe_enabled:
        operational_ready = True
        readiness_basis = "configuration_only"
        degraded_reason = None
    else:
        assert configured_base_url is not None
        operational_ready = probe_dependency_health(configured_base_url)
        readiness_basis = "probe_succeeded" if operational_ready else "probe_failed"
        if operational_ready:
            degraded_reason = None

    return IntegrationDependencyState(
        key=key,
        service_name=service_name,
        description=description,
        base_url_env=base_url_env,
        base_url=public_base_url,
        configured=configured,
        operational_ready=operational_ready,
        runtime_probe_enabled=probe_enabled,
        readiness_basis=readiness_basis,
        degraded_reason=degraded_reason,
    )
