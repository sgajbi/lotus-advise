import os
from dataclasses import dataclass
from typing import cast
from urllib.parse import SplitResult, urlsplit, urlunsplit

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


@dataclass(frozen=True)
class _DependencyConfiguration:
    configured_base_url: str | None
    public_base_url: str | None

    @property
    def configured(self) -> bool:
        return self.configured_base_url is not None

    @property
    def valid(self) -> bool:
        return self.public_base_url is not None


@dataclass(frozen=True)
class _DependencyReadiness:
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
    probe_base_url = sanitized_http_base_url(base_url)
    if probe_base_url is None:
        return False
    timeout = httpx.Timeout(connect=0.5, read=0.75, write=0.75, pool=0.5)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            return _probe_health_endpoints(client, probe_base_url)
    except httpx.HTTPError:
        return False


def _probe_health_endpoints(client: httpx.Client, probe_base_url: str) -> bool:
    ready_response = _probe_health_endpoint(client, probe_base_url, "/health/ready")
    if ready_response == 200:
        return True
    if ready_response is not None:
        return False

    health_response = _probe_health_endpoint(client, probe_base_url, "/health")
    return health_response == 200


def _probe_health_endpoint(
    client: httpx.Client,
    probe_base_url: str,
    endpoint: str,
) -> int | None:
    try:
        response = client.get(f"{probe_base_url}{endpoint}")
    except httpx.HTTPError:
        return None
    return cast(int, response.status_code)


def _is_http_probe_base_url(base_url: str) -> bool:
    return sanitized_http_base_url(base_url) is not None


def sanitized_http_base_url(base_url: str | None) -> str | None:
    split = _split_http_base_url(base_url)
    if split is None:
        return None
    netloc = _sanitized_netloc(split)
    if netloc is None:
        return None
    return urlunsplit((split.scheme, netloc, split.path.rstrip("/"), "", ""))


def _split_http_base_url(base_url: str | None) -> SplitResult | None:
    if base_url is None or not base_url.strip():
        return None
    split = urlsplit(base_url.strip())
    if split.scheme not in {"http", "https"} or split.hostname is None:
        return None
    return split


def _sanitized_netloc(split: SplitResult) -> str | None:
    try:
        port = split.port
    except ValueError:
        return None
    netloc = split.hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    return netloc


def public_dependency_base_url(base_url: str | None) -> str | None:
    return sanitized_http_base_url(base_url)


def build_dependency_state(
    *,
    key: str,
    service_name: str,
    description: str,
    base_url_env: str,
) -> IntegrationDependencyState:
    configuration = _dependency_configuration(base_url_env)
    readiness = _dependency_readiness(key=key, configuration=configuration)

    return IntegrationDependencyState(
        key=key,
        service_name=service_name,
        description=description,
        base_url_env=base_url_env,
        base_url=configuration.public_base_url,
        configured=configuration.configured,
        operational_ready=readiness.operational_ready,
        runtime_probe_enabled=readiness.runtime_probe_enabled,
        readiness_basis=readiness.readiness_basis,
        degraded_reason=readiness.degraded_reason,
    )


def _dependency_configuration(base_url_env: str) -> _DependencyConfiguration:
    configured_base_url = os.getenv(base_url_env, "").strip() or None
    return _DependencyConfiguration(
        configured_base_url=configured_base_url,
        public_base_url=public_dependency_base_url(configured_base_url),
    )


def _dependency_readiness(
    *,
    key: str,
    configuration: _DependencyConfiguration,
) -> _DependencyReadiness:
    unavailable_reason = _dependency_unavailable_reason(key)
    if not configuration.configured:
        return _DependencyReadiness(False, False, "not_configured", unavailable_reason)
    if not configuration.valid:
        return _DependencyReadiness(False, False, "invalid_configuration", unavailable_reason)
    if not runtime_dependency_probing_enabled():
        return _DependencyReadiness(True, False, "configuration_only", None)
    return _probed_dependency_readiness(configuration.public_base_url, unavailable_reason)


def _probed_dependency_readiness(
    public_base_url: str | None,
    unavailable_reason: str,
) -> _DependencyReadiness:
    if public_base_url is None:
        return _DependencyReadiness(False, False, "invalid_configuration", unavailable_reason)
    operational_ready = probe_dependency_health(public_base_url)
    if operational_ready:
        return _DependencyReadiness(True, True, "probe_succeeded", None)
    return _DependencyReadiness(False, True, "probe_failed", unavailable_reason)


def _dependency_unavailable_reason(key: str) -> str:
    return f"{key.upper().replace('-', '_')}_DEPENDENCY_UNAVAILABLE"
