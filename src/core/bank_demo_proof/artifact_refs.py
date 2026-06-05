from __future__ import annotations

import re
from urllib.parse import SplitResult, urlsplit

_SENSITIVE_REF_FRAGMENTS = (
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
    "raw_prompt",
    "raw_source",
    "provider_output",
    "provider_response",
    "trace_id",
    "correlation_id",
)
_WINDOWS_DRIVE_REF = re.compile(r"^[A-Za-z]:")


def normalize_output_ref_prefix(value: str) -> str:
    return normalize_local_artifact_ref(value, field_name="output_ref_prefix").rstrip("/")


def normalize_optional_local_artifact_ref(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_local_artifact_ref(value, field_name=field_name)


def normalize_local_artifact_ref(value: str, *, field_name: str) -> str:
    normalized = value.strip().replace("\\", "/")
    _validate_local_artifact_ref_text(normalized, field_name=field_name)
    parsed = urlsplit(normalized)
    _validate_local_artifact_ref_location(normalized, parsed, field_name=field_name)
    path_parts = _local_artifact_ref_path_parts(normalized, field_name=field_name)
    return "/".join(path_parts)


def _validate_local_artifact_ref_text(normalized: str, *, field_name: str) -> None:
    if not normalized:
        raise ValueError(f"{field_name} must be a relative local artifact path")
    if any(char in normalized for char in ("\r", "\n", "\t", "\x00")):
        raise ValueError(f"{field_name} cannot contain control characters")


def _validate_local_artifact_ref_location(
    normalized: str, parsed: SplitResult, *, field_name: str
) -> None:
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include URL scheme, authority, query, or fragment")
    if normalized.startswith("/") or _WINDOWS_DRIVE_REF.match(normalized):
        raise ValueError(f"{field_name} must be relative, not absolute")


def _local_artifact_ref_path_parts(normalized: str, *, field_name: str) -> list[str]:
    path_parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in path_parts):
        raise ValueError(f"{field_name} cannot contain parent-directory traversal")
    if any(_is_sensitive_fragment(part) for part in path_parts):
        raise ValueError(f"{field_name} cannot contain sensitive material")
    return path_parts


def _is_sensitive_fragment(value: str) -> bool:
    normalized = re.sub(r"[-\s]+", "_", value.lower())
    return any(fragment in normalized for fragment in _SENSITIVE_REF_FRAGMENTS)
