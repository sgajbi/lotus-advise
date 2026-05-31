SENSITIVE_ERROR_DETAIL_FRAGMENTS = (
    "authorization",
    "bearer ",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "raw prompt",
    "raw payload",
    "raw source",
    "provider response",
)


def contains_sensitive_error_detail(error_detail: str) -> bool:
    normalized = error_detail.lower().replace("-", " ").replace("_", " ")
    return any(
        fragment.replace("-", " ").replace("_", " ") in normalized
        for fragment in SENSITIVE_ERROR_DETAIL_FRAGMENTS
    )
