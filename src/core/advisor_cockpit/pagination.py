from __future__ import annotations

COCKPIT_ACTION_DEFAULT_PAGE_SIZE = 25
COCKPIT_ACTION_MAX_PAGE_SIZE = 100


def normalize_cockpit_page_size(limit: int | None) -> int:
    if limit is None:
        return COCKPIT_ACTION_DEFAULT_PAGE_SIZE
    if limit < 1:
        return COCKPIT_ACTION_DEFAULT_PAGE_SIZE
    return min(limit, COCKPIT_ACTION_MAX_PAGE_SIZE)
