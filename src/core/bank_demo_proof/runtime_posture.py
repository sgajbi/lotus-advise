from __future__ import annotations

import re
from numbers import Number
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator

_SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "prompt",
    "raw_payload",
    "raw_source",
    "source_input_hash",
    "trace_id",
    "correlation_id",
)
_MAX_SUMMARY_KEYS = 32
_MAX_SUMMARY_LIST_ITEMS = 50
_MAX_SUMMARY_STRING_LENGTH = 512
_MAX_BASE_URL_LENGTH = 512
_MAX_ENDPOINT_PATH_LENGTH = 160
_MAX_RUNTIME_ENDPOINTS = 32
_URL_PATTERN = re.compile(r"https?://[^\s]+")
_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(
        r"\b(?:api[-_ ]?key|authorization|cookie|password|secret|token)\b\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:correlation[-_ ]?id|trace[-_ ]?id|raw[-_ ]?(?:payload|prompt|source)|"
        r"provider[-_ ]?(?:response|output))"
        r"\b\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\bprovider[-_ ]?(?:response|output)\b", re.IGNORECASE),
    re.compile(r"traceback \(most recent call last\)", re.IGNORECASE),
)


class RuntimeEndpointEvidence(BaseModel):
    endpoint: str = Field(
        description="Runtime endpoint that was probed.",
        examples=["/health/ready"],
        min_length=1,
        max_length=_MAX_ENDPOINT_PATH_LENGTH,
    )
    http_status: int | None = Field(
        default=None,
        description="Observed HTTP status, or null when the endpoint was not probed.",
    )
    posture: Literal["READY", "DEGRADED", "UNAVAILABLE", "NOT_PROBED"] = Field(
        description="Bounded runtime posture for this endpoint.",
        examples=["READY"],
    )
    latency_ms: int | None = Field(
        default=None,
        ge=0,
        le=60_000,
        description="Bounded endpoint probe latency in milliseconds, when observed.",
        examples=[12],
    )
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized, bounded endpoint summary.",
    )

    @field_validator("endpoint")
    @classmethod
    def _endpoint_must_be_a_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("/") or "?" in normalized or "#" in normalized:
            raise ValueError("runtime endpoint evidence must use a path without query or fragment")
        if any(char.isspace() for char in normalized):
            raise ValueError("runtime endpoint evidence cannot contain whitespace")
        return normalized

    @field_validator("latency_ms")
    @classmethod
    def _latency_must_be_integer_ms(cls, value: int | None) -> int | None:
        return value

    @field_validator("summary")
    @classmethod
    def _summary_must_be_sanitized(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _sanitize_summary_dict(value)


class BackendRuntimePosture(BaseModel):
    service_name: Literal["lotus-advise"] = Field(default="lotus-advise")
    base_url: str = Field(
        description="Runtime base URL used for endpoint probes.",
        examples=["https://advise.dev.lotus"],
        min_length=1,
        max_length=_MAX_BASE_URL_LENGTH,
    )
    environment: str = Field(description="Runtime environment label.", examples=["local"])
    endpoints: list[RuntimeEndpointEvidence] = Field(
        min_length=1,
        max_length=_MAX_RUNTIME_ENDPOINTS,
        description="Sanitized health, readiness, capability, and runtime evidence.",
    )

    @field_validator("base_url")
    @classmethod
    def _base_url_must_not_carry_secrets(cls, value: str) -> str:
        return normalize_runtime_base_url(value)

    @field_validator("environment")
    @classmethod
    def _environment_must_be_bounded(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or len(normalized) > 64:
            raise ValueError("runtime environment label must be present and bounded")
        if any(fragment in normalized.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS):
            raise ValueError("runtime environment label cannot contain sensitive material")
        return normalized


def _sanitize_summary_dict(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for index, (key, value) in enumerate(payload.items()):
        if index >= _MAX_SUMMARY_KEYS:
            sanitized["truncated"] = True
            break
        normalized_key = str(key)
        if _is_sensitive_key(normalized_key):
            sanitized[normalized_key] = "[REDACTED]"
            continue
        sanitized[normalized_key] = _sanitize_summary_value(value)
    return sanitized


def normalize_runtime_base_url(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > _MAX_BASE_URL_LENGTH:
        raise ValueError("runtime base_url must be present and bounded")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("runtime base_url must be an http(s) URL with a host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("runtime base_url cannot include credentials, query, or fragment")
    netloc = parsed.hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, netloc, path, "", ""))


def _sanitize_summary_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitize_summary_dict(value)
    if isinstance(value, list):
        return [_sanitize_summary_value(item) for item in value[:_MAX_SUMMARY_LIST_ITEMS]]
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, bool) or isinstance(value, Number) or value is None:
        return value
    return str(type(value).__name__)


def _sanitize_string(value: str) -> str:
    normalized = value.replace("\r", " ").replace("\n", " ").strip()
    normalized = _URL_PATTERN.sub(lambda match: _sanitize_url_text(match.group(0)), normalized)
    if _contains_sensitive_value(normalized):
        return "[REDACTED]"
    parsed = urlsplit(normalized)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        normalized = _sanitize_url_text(normalized)
    if len(normalized) > _MAX_SUMMARY_STRING_LENGTH:
        return f"{normalized[:_MAX_SUMMARY_STRING_LENGTH]}..."
    return normalized


def _sanitize_url_text(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        netloc = parsed.hostname
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path.rstrip("/"), "", ""))
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(" ", "_")
    return any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS)


def _contains_sensitive_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SENSITIVE_VALUE_PATTERNS)
