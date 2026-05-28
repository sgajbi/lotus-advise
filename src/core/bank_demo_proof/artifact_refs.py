from __future__ import annotations

import re
from urllib.parse import urlsplit

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
    "raw_source",
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
    if not normalized:
        raise ValueError(f"{field_name} must be a relative local artifact path")
    if any(char in normalized for char in ("\r", "\n", "\t", "\x00")):
        raise ValueError(f"{field_name} cannot contain control characters")
    parsed = urlsplit(normalized)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include URL scheme, authority, query, or fragment")
    if normalized.startswith("/") or _WINDOWS_DRIVE_REF.match(normalized):
        raise ValueError(f"{field_name} must be relative, not absolute")
    path_parts = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in path_parts):
        raise ValueError(f"{field_name} cannot contain parent-directory traversal")
    if any(_is_sensitive_fragment(part) for part in path_parts):
        raise ValueError(f"{field_name} cannot contain sensitive material")
    return "/".join(path_parts)


def _is_sensitive_fragment(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return any(fragment in normalized for fragment in _SENSITIVE_REF_FRAGMENTS)
