MAX_IDEMPOTENCY_KEY_LENGTH = 128


def _contains_control_character(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def normalize_optional_idempotency_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    normalized = idempotency_key.strip()
    if (
        not normalized
        or len(normalized) > MAX_IDEMPOTENCY_KEY_LENGTH
        or _contains_control_character(normalized)
    ):
        return None
    return normalized


def normalize_required_idempotency_key(idempotency_key: str | None) -> str:
    normalized = normalize_optional_idempotency_key(idempotency_key)
    if normalized is None:
        raise ValueError("IDEMPOTENCY_KEY_REQUIRED")
    return normalized
