from uuid import uuid4


def normalize_optional_correlation_id(correlation_id: str | None) -> str | None:
    if correlation_id is None:
        return None
    stripped = correlation_id.strip()
    return stripped or None


def resolve_correlation_id(correlation_id: str | None) -> str:
    normalized = normalize_optional_correlation_id(correlation_id)
    if normalized is not None:
        return normalized
    return f"corr_{uuid4().hex[:12]}"
