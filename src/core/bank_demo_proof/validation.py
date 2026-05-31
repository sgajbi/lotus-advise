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


def normalize_rfc28_business_text(
    value: str,
    *,
    field_name: str,
    max_length: int | None = None,
) -> str:
    normalized = normalize_required_rfc28_text(
        value,
        field_name=field_name,
        max_length=max_length,
    )
    if contains_sensitive_rfc28_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def normalize_required_rfc28_text(
    value: str,
    *,
    field_name: str,
    max_length: int | None = None,
) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if max_length is not None and len(normalized) > max_length:
        raise ValueError(f"{field_name} is too long")
    return normalized


def normalize_capture_text(
    value: str,
    *,
    field_name: str,
    max_length: int = RFC28_CAPTURE_IDENTIFIER_MAX_LENGTH,
) -> str:
    return normalize_rfc28_business_text(
        value,
        field_name=field_name,
        max_length=max_length,
    )


def contains_sensitive_capture_term(value: str) -> bool:
    return contains_sensitive_rfc28_term(value)


def contains_sensitive_rfc28_term(value: str) -> bool:
    lowered = value.lower().replace("-", " ").replace("_", " ")
    return any(term in lowered for term in RFC28_CAPTURE_SENSITIVE_TERMS)
