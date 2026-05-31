def normalize_optional_idempotency_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    normalized = idempotency_key.strip()
    if not normalized:
        return None
    return normalized


def normalize_required_idempotency_key(idempotency_key: str | None) -> str:
    normalized = normalize_optional_idempotency_key(idempotency_key)
    if normalized is None:
        raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
    return normalized
