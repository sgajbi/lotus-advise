import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.core.proposals.correlation import (
    MAX_CORRELATION_ID_LENGTH,
    normalize_optional_correlation_id,
)

logger = logging.getLogger("enterprise_readiness")
MiddlewareNext = Callable[[Request], Awaitable[Response]]
MiddlewareCallable = Callable[[Request, MiddlewareNext], Awaitable[Response]]

_SERVICE_NAME = "lotus-advise"
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_REQUIRED_HEADERS = {"x-actor-id", "x-tenant-id", "x-role", "x-correlation-id"}
_REDACT_FIELD_MARKERS = frozenset(
    {
        "access_key",
        "account_number",
        "api_key",
        "authorization",
        "client_email",
        "cookie",
        "password",
        "private_key",
        "secret",
        "session",
        "ssn",
        "token",
    }
)
_REDACTED_VALUE = "***REDACTED***"


def _env_enabled(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _load_json_map(name: str) -> dict[str, Any]:
    raw = os.getenv(name, "{}")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_map_config_issue(name: str, issue: str) -> str | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return issue
    return None if isinstance(parsed, dict) else issue


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def enterprise_policy_version() -> str:
    return os.getenv("ENTERPRISE_POLICY_VERSION", "1.0.0")


def validate_enterprise_runtime_config() -> list[str]:
    issues: list[str] = []
    if not enterprise_policy_version().strip():
        issues.append("missing_policy_version")

    rotation_days = _env_int("ENTERPRISE_SECRET_ROTATION_DAYS", 90)
    if rotation_days <= 0 or rotation_days > 90:
        issues.append("secret_rotation_days_out_of_range")

    if (
        _env_enabled("ENTERPRISE_ENFORCE_AUTHZ", "false")
        and not os.getenv("ENTERPRISE_PRIMARY_KEY_ID", "").strip()
    ):
        issues.append("missing_primary_key_id")
    for issue in (
        _json_map_config_issue(
            "ENTERPRISE_FEATURE_FLAGS_JSON",
            "invalid_feature_flags_json",
        ),
        _json_map_config_issue(
            "ENTERPRISE_CAPABILITY_RULES_JSON",
            "invalid_capability_rules_json",
        ),
    ):
        if issue is not None:
            issues.append(issue)

    if issues and _env_enabled("ENTERPRISE_ENFORCE_RUNTIME_CONFIG", "false"):
        raise RuntimeError(f"enterprise_runtime_config_invalid:{','.join(issues)}")
    return issues


def load_feature_flags() -> dict[str, dict[str, dict[str, bool]]]:
    return _load_json_map("ENTERPRISE_FEATURE_FLAGS_JSON")


def load_capability_rules() -> dict[str, str]:
    rules = _load_json_map("ENTERPRISE_CAPABILITY_RULES_JSON")
    normalized: dict[str, str] = {}
    for key, value in rules.items():
        if not isinstance(key, str):
            continue
        capability_rule = key.strip()
        capability = str(value).strip()
        if capability_rule and capability:
            normalized[capability_rule] = capability
    return normalized


def is_feature_enabled(feature_key: str, tenant_id: str, role: str) -> bool:
    flags = load_feature_flags()
    feature = flags.get(feature_key, {})
    tenant = feature.get(tenant_id, {})
    explicit = tenant.get(role)
    if isinstance(explicit, bool):
        return explicit
    tenant_default = tenant.get("*")
    if isinstance(tenant_default, bool):
        return tenant_default
    global_default = feature.get("*", {}).get("*")
    return bool(global_default) if isinstance(global_default, bool) else False


def _required_capability(method: str, path: str) -> str | None:
    method = method.upper()
    for key, capability in load_capability_rules().items():
        prefix = f"{method} "
        if key.upper().startswith(prefix) and _path_matches_capability_rule(
            request_path=path,
            rule_path=key[len(prefix) :],
        ):
            return capability
    return None


def _path_matches_capability_rule(*, request_path: str, rule_path: str) -> bool:
    normalized_rule = rule_path.rstrip("/")
    normalized_request = request_path.rstrip("/")
    return normalized_request == normalized_rule or normalized_request.startswith(
        f"{normalized_rule}/"
    )


def authorize_write_request(
    method: str, path: str, headers: dict[str, str]
) -> tuple[bool, str | None]:
    if not _should_enforce_write_authorization(method):
        return True, None

    normalized = _normalize_headers(headers)
    missing = _missing_required_enterprise_headers(normalized)
    if missing:
        return False, f"missing_headers:{','.join(missing)}"

    if not _has_service_identity(normalized):
        return False, "missing_service_identity"

    capability_rule_issue = _capability_rule_config_issue()
    if capability_rule_issue is not None:
        return False, capability_rule_issue

    missing_capability = _missing_required_capability(method, path, normalized)
    if missing_capability is not None:
        return False, f"missing_capability:{missing_capability}"

    return True, None


def _should_enforce_write_authorization(method: str) -> bool:
    return method.upper() in _WRITE_METHODS and _env_enabled("ENTERPRISE_ENFORCE_AUTHZ", "false")


def _normalize_headers(headers: dict[str, str]) -> dict[str, str]:
    return {str(key).strip().lower(): str(value).strip() for key, value in headers.items()}


def _missing_required_enterprise_headers(headers: dict[str, str]) -> list[str]:
    return sorted(header for header in _REQUIRED_HEADERS if not headers.get(header))


def _has_service_identity(headers: dict[str, str]) -> bool:
    return bool(headers.get("x-service-identity") or headers.get("authorization"))


def _capability_rule_config_issue() -> str | None:
    return _json_map_config_issue(
        "ENTERPRISE_CAPABILITY_RULES_JSON",
        "invalid_capability_rules_json",
    )


def _missing_required_capability(
    method: str,
    path: str,
    headers: dict[str, str],
) -> str | None:
    required_capability = _required_capability(method, path)
    if required_capability is None:
        return None

    if required_capability in _request_capabilities(headers):
        return None
    return required_capability


def _request_capabilities(headers: dict[str, str]) -> set[str]:
    return {part.strip() for part in headers.get("x-capabilities", "").split(",") if part.strip()}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_field_name(key):
                out[key] = _REDACTED_VALUE
            else:
                out[key] = redact_sensitive(item)
        return out
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def _is_sensitive_field_name(key: Any) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    compact = normalized.replace("_", "")
    return any(
        marker in normalized or marker.replace("_", "") in compact
        for marker in _REDACT_FIELD_MARKERS
    )


def _normalize_audit_identity(value: str, *, default: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > MAX_CORRELATION_ID_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in normalized)
    ):
        return default
    return normalized


def emit_audit_event(
    *,
    action: str,
    actor_id: str,
    tenant_id: str,
    role: str,
    correlation_id: str | None,
    metadata: dict[str, Any],
) -> None:
    normalized_correlation_id = normalize_optional_correlation_id(correlation_id)
    logger.info(
        "enterprise_audit_event",
        extra={
            "audit": {
                "service": _SERVICE_NAME,
                "action": action,
                "actor_id": _normalize_audit_identity(actor_id, default="unknown"),
                "tenant_id": _normalize_audit_identity(tenant_id, default="default"),
                "role": _normalize_audit_identity(role, default="unknown"),
                "correlation_id": normalized_correlation_id or "",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "policy_version": enterprise_policy_version(),
                "metadata": redact_sensitive(metadata),
            }
        },
    )


def _enterprise_policy_response(*, status_code: int, content: dict[str, Any]) -> JSONResponse:
    response = JSONResponse(status_code=status_code, content=content)
    response.headers["X-Enterprise-Policy-Version"] = enterprise_policy_version()
    return response


def build_enterprise_audit_middleware() -> MiddlewareCallable:
    async def middleware(request: Request, call_next: MiddlewareNext) -> Response:
        max_write_payload_bytes = _env_int("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", 1_048_576)
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            content_length = 0
        if request.method in _WRITE_METHODS and content_length > max_write_payload_bytes:
            emit_audit_event(
                action=f"DENY {request.method} {request.url.path}",
                actor_id=request.headers.get("X-Actor-Id", "unknown"),
                tenant_id=request.headers.get("X-Tenant-Id", "default"),
                role=request.headers.get("X-Role", "unknown"),
                correlation_id=request.headers.get("X-Correlation-Id"),
                metadata={
                    "reason": "payload_too_large",
                    "content_length": content_length,
                    "max_write_payload_bytes": max_write_payload_bytes,
                },
            )
            return _enterprise_policy_response(
                status_code=413,
                content={"detail": "payload_too_large"},
            )

        authorized, reason = authorize_write_request(
            request.method, request.url.path, dict(request.headers)
        )
        if not authorized:
            emit_audit_event(
                action=f"DENY {request.method} {request.url.path}",
                actor_id=request.headers.get("X-Actor-Id", "unknown"),
                tenant_id=request.headers.get("X-Tenant-Id", "default"),
                role=request.headers.get("X-Role", "unknown"),
                correlation_id=request.headers.get("X-Correlation-Id"),
                metadata={"reason": reason},
            )
            return _enterprise_policy_response(
                status_code=403, content={"detail": "authorization_policy_denied", "reason": reason}
            )

        response = await call_next(request)
        response.headers["X-Enterprise-Policy-Version"] = enterprise_policy_version()
        if request.method in _WRITE_METHODS:
            emit_audit_event(
                action=f"{request.method} {request.url.path}",
                actor_id=request.headers.get("X-Actor-Id", "unknown"),
                tenant_id=request.headers.get("X-Tenant-Id", "default"),
                role=request.headers.get("X-Role", "unknown"),
                correlation_id=request.headers.get("X-Correlation-Id"),
                metadata={"status_code": response.status_code},
            )
        return response

    return middleware
