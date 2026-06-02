from __future__ import annotations

import hashlib
from typing import cast

from src.core.proposals.correlation import normalize_optional_correlation_id


def resolve_advisory_copilot_correlation_id(correlation_id: str | None, *, fallback: str) -> str:
    normalized = normalize_optional_correlation_id(correlation_id)
    if normalized is not None:
        return cast(str, normalized)
    fallback_id = normalize_optional_correlation_id(fallback)
    if fallback_id is not None:
        return cast(str, fallback_id)
    digest = hashlib.sha256(fallback.encode("utf-8")).hexdigest()[:24]
    return f"corr-{digest}"
