from __future__ import annotations

RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH = 160
RFC28_CAPTURE_METADATA_LABEL_MAX_LENGTH = 64
RFC28_CAPTURE_SOURCE_PATH_MAX_LENGTH = 240
RFC28_CAPTURE_OBSERVED_VALUE_MAX_LENGTH = 512
RFC28_CAPTURE_CLAIM_REFS_MAX_ITEMS = 64
RFC28_CAPTURE_SENSITIVE_TERMS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "raw prompt",
    "raw payload",
    "provider response",
)


def normalize_capture_text(
    value: str,
    *,
    field_name: str,
    max_length: int = RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} is too long")
    if contains_sensitive_capture_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def contains_sensitive_capture_term(value: str) -> bool:
    lowered = value.lower().replace("-", " ")
    return any(term in lowered for term in RFC28_CAPTURE_SENSITIVE_TERMS)
