from __future__ import annotations

from urllib.parse import SplitResult, urlsplit

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
    "provider output",
    "trace id",
    "correlation id",
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


def normalize_lotus_advise_contract_ref(value: str, *, field_name: str) -> str:
    normalized = normalize_required_rfc28_text(value, field_name=field_name, max_length=512)
    parsed = urlsplit(normalized)
    path_parts = _lotus_advise_contract_path_parts(parsed)
    _reject_control_characters(normalized, field_name=field_name)
    _require_lotus_advise_contract_ref(parsed, field_name=field_name)
    _reject_contract_ref_credentials_query_or_fragment(parsed, field_name=field_name)
    _require_contract_path(path_parts, field_name=field_name)
    _reject_contract_ref_path_traversal(path_parts, field_name=field_name)
    if contains_sensitive_rfc28_term(normalized):
        raise ValueError(f"{field_name} cannot contain sensitive technical detail")
    return normalized


def _reject_control_characters(value: str, *, field_name: str) -> None:
    if any(char in value for char in ("\r", "\n", "\t", "\x00")):
        raise ValueError(f"{field_name} cannot contain control characters")


def _require_lotus_advise_contract_ref(parsed: SplitResult, *, field_name: str) -> None:
    if parsed.scheme != "lotus-advise" or not parsed.netloc:
        raise ValueError(f"{field_name} must be a lotus-advise logical contract reference")


def _reject_contract_ref_credentials_query_or_fragment(
    parsed: SplitResult, *, field_name: str
) -> None:
    if parsed.query or parsed.fragment or "@" in parsed.netloc:
        raise ValueError(f"{field_name} must not include credentials, query, or fragment")


def _lotus_advise_contract_path_parts(parsed: SplitResult) -> list[str]:
    return [part for part in parsed.path.split("/") if part]


def _require_contract_path(path_parts: list[str], *, field_name: str) -> None:
    if not path_parts:
        raise ValueError(f"{field_name} must include a contract path")


def _reject_contract_ref_path_traversal(path_parts: list[str], *, field_name: str) -> None:
    if any(part == ".." for part in path_parts):
        raise ValueError(f"{field_name} cannot contain parent-directory traversal")
