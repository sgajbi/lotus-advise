from __future__ import annotations


def normalize_required_copilot_reference_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def normalize_optional_copilot_reference_text(
    value: str | None,
    *,
    error_code: str,
) -> str | None:
    if value is None:
        return None
    return normalize_required_copilot_reference_text(value, error_code=error_code)
