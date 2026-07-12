from __future__ import annotations

DEFAULT_WORKSPACE_SESSION_CACHE_SIZE = 500


def validate_workspace_session_cache_size(max_size: int) -> int:
    if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 1:
        raise ValueError("WORKSPACE_SESSION_CACHE_SIZE_INVALID")
    return max_size
