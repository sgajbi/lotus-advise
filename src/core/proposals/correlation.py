from uuid import uuid4


def resolve_correlation_id(correlation_id: str | None) -> str:
    return correlation_id or f"corr_{uuid4().hex[:12]}"
