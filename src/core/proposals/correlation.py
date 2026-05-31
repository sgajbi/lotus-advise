from uuid import uuid4

MAX_CORRELATION_ID_LENGTH = 128


def _contains_control_character(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def normalize_optional_correlation_id(correlation_id: str | None) -> str | None:
    if correlation_id is None:
        return None
    stripped = correlation_id.strip()
    if (
        not stripped
        or len(stripped) > MAX_CORRELATION_ID_LENGTH
        or _contains_control_character(stripped)
    ):
        return None
    return stripped


def resolve_correlation_id(correlation_id: str | None) -> str:
    normalized = normalize_optional_correlation_id(correlation_id)
    if normalized is not None:
        return normalized
    return f"corr_{uuid4().hex[:12]}"
