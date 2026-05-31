from uuid import uuid4


def resolve_correlation_id(correlation_id: str | None) -> str:
    if correlation_id is not None:
        stripped = correlation_id.strip()
        if stripped:
            return stripped
    return f"corr_{uuid4().hex[:12]}"
