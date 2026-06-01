from __future__ import annotations

import re

SENSITIVE_ERROR_DETAIL_FRAGMENTS = (
    "authorization",
    "bearer ",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "raw prompt",
    "raw payload",
    "raw source",
    "provider response",
    "provider output",
)

SENSITIVE_ERROR_DETAIL_PATTERNS = (
    re.compile(r"\btrace[-_ ]?id\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bcorrelation[-_ ]?id\s*[:=]\s*\S+", re.IGNORECASE),
)


def contains_sensitive_error_detail(error_detail: str) -> bool:
    normalized = error_detail.lower().replace("-", " ").replace("_", " ")
    return any(pattern.search(error_detail) for pattern in SENSITIVE_ERROR_DETAIL_PATTERNS) or any(
        fragment.replace("-", " ").replace("_", " ") in normalized
        for fragment in SENSITIVE_ERROR_DETAIL_FRAGMENTS
    )
