from __future__ import annotations


def normalize_required_actor_id(value: str, *, error_code: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(error_code)
    return normalized


def normalize_optional_support_note(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None
