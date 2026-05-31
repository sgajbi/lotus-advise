from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from src.core.proposals.exceptions import ProposalValidationError

COCKPIT_ACTION_DEFAULT_PAGE_SIZE = 25
COCKPIT_ACTION_MAX_PAGE_SIZE = 100
T = TypeVar("T")


def normalize_cockpit_page_size(limit: int | None) -> int:
    if limit is None:
        return COCKPIT_ACTION_DEFAULT_PAGE_SIZE
    if limit < 1:
        return COCKPIT_ACTION_DEFAULT_PAGE_SIZE
    return min(limit, COCKPIT_ACTION_MAX_PAGE_SIZE)


def cockpit_cursor_start(
    *,
    items: Sequence[T],
    cursor: str | None,
    identity: Callable[[T], str],
    invalid_code: str,
) -> int:
    if cursor is None:
        return 0
    for index, item in enumerate(items):
        if identity(item) == cursor:
            return index + 1
    raise ProposalValidationError(invalid_code)
