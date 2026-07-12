"""HTTP boundary controls for the Lotus Advise API."""

from __future__ import annotations

import os
from collections.abc import Iterable

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import Response

_PRODUCTION_LIKE_ENVIRONMENTS = frozenset({"prod", "production", "staging", "uat"})
_DEFAULT_LOCAL_TRUSTED_HOSTS = (
    "testserver",
    "localhost",
    "127.0.0.1",
    "::1",
    "*.local",
    "*.dev.lotus",
    "host.docker.internal",
)
_CORS_ALLOW_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
_CORS_ALLOW_HEADERS = (
    "Authorization",
    "Content-Type",
    "Idempotency-Key",
    "X-Actor-Id",
    "X-Authorized-Advisor-Id",
    "X-Authorized-Portfolio-Id",
    "X-Authorized-Proposal-Id",
    "X-Capabilities",
    "X-Correlation-Id",
    "X-Legal-Entity-Code",
    "X-Principal-Status",
    "X-Request-Id",
    "X-Role",
    "X-Service-Identity",
    "X-Tenant-Id",
    "traceparent",
)
_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        apply_security_headers(response)
        return response


def install_http_boundary(app: FastAPI) -> None:
    allowed_origins = configured_allowed_origins()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(configured_trusted_hosts()))
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(allowed_origins),
            allow_methods=list(_CORS_ALLOW_METHODS),
            allow_headers=list(_CORS_ALLOW_HEADERS),
            allow_credentials=False,
        )
    app.add_middleware(SecurityHeadersMiddleware)


def apply_security_headers(response: Response) -> None:
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)


def approved_security_headers() -> dict[str, str]:
    return dict(_SECURITY_HEADERS)


def configured_trusted_hosts() -> tuple[str, ...]:
    return _configured_values("HTTP_BOUNDARY_TRUSTED_HOSTS") or _DEFAULT_LOCAL_TRUSTED_HOSTS


def configured_allowed_origins() -> tuple[str, ...]:
    return _configured_values("HTTP_BOUNDARY_ALLOWED_ORIGINS")


def http_boundary_config_issues() -> list[str]:
    issues: list[str] = []
    trusted_hosts = _configured_values("HTTP_BOUNDARY_TRUSTED_HOSTS")
    allowed_origins = _configured_values("HTTP_BOUNDARY_ALLOWED_ORIGINS")
    if _is_production_like_environment() and not trusted_hosts:
        issues.append("missing_http_trusted_hosts")
    if _contains_control_character(trusted_hosts):
        issues.append("invalid_http_trusted_hosts")
    if _contains_control_character(allowed_origins):
        issues.append("invalid_http_allowed_origins")
    if _is_production_like_environment() and _contains_wildcard(trusted_hosts):
        issues.append("wildcard_http_trusted_host")
    if _is_production_like_environment() and _contains_wildcard(allowed_origins):
        issues.append("wildcard_http_allowed_origin")
    return issues


def _configured_values(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _is_production_like_environment() -> bool:
    return os.getenv("ENVIRONMENT", "").strip().lower() in _PRODUCTION_LIKE_ENVIRONMENTS


def _contains_wildcard(values: Iterable[str]) -> bool:
    return any("*" in value for value in values)


def _contains_control_character(values: Iterable[str]) -> bool:
    return any(any(ord(char) < 32 or ord(char) == 127 for char in value) for value in values)
