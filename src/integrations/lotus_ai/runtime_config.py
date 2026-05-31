from __future__ import annotations

import os
from typing import cast

from src.integrations.base import sanitized_http_base_url


def resolve_lotus_ai_base_url(
    *,
    unavailable_error_type: type[Exception],
    unavailable_message: str,
) -> str:
    base_url = sanitized_http_base_url(os.getenv("LOTUS_AI_BASE_URL"))
    if base_url is not None:
        return cast(str, base_url)
    raise unavailable_error_type(unavailable_message)
