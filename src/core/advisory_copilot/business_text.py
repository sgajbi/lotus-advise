from __future__ import annotations

_COPILOT_BUSINESS_COPY_TECHNICAL_TERMS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api key",
    "apikey",
    "raw prompt",
    "provider response",
    "provider output",
    "trace id",
    "correlation id",
    "run ledger",
    "raw payload",
    "raw source",
)


def assert_copilot_business_safe_text(
    *values: str,
    error_code: str = "COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL",
) -> None:
    if contains_copilot_business_technical_detail(" ".join(values)):
        raise ValueError(error_code)


def normalize_required_copilot_business_text(
    value: str,
    *,
    error_code: str,
    technical_error_code: str = "COPILOT_EVIDENCE_TEXT_LEAKS_TECHNICAL_DETAIL",
) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    assert_copilot_business_safe_text(normalized, error_code=technical_error_code)
    return normalized


def contains_copilot_business_technical_detail(value: str) -> bool:
    normalized = value.lower().replace("-", " ").replace("_", " ")
    return any(term in normalized for term in _COPILOT_BUSINESS_COPY_TECHNICAL_TERMS)
