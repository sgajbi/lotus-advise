from __future__ import annotations

import os
from typing import cast

from src.integrations.base import sanitized_http_base_url

_MAX_LOTUS_AI_TENANT_ID_LENGTH = 128


class LotusAITenantIdentityError(ValueError):
    """Raised when Lotus AI caller identity cannot be safely resolved."""


def resolve_lotus_ai_base_url(
    *,
    unavailable_error_type: type[Exception],
    unavailable_message: str,
) -> str:
    base_url = sanitized_http_base_url(os.getenv("LOTUS_AI_BASE_URL"))
    if base_url is not None:
        return cast(str, base_url)
    raise unavailable_error_type(unavailable_message)


def resolve_lotus_ai_tenant_id() -> str:
    normalized = _configured_lotus_ai_tenant_id()
    if _is_supported_lotus_ai_tenant_id(normalized):
        return normalized
    raise LotusAITenantIdentityError("LOTUS_AI_TENANT_ID_UNAVAILABLE")


def _configured_lotus_ai_tenant_id() -> str:
    return os.getenv("LOTUS_ADVISE_TENANT_ID", "").strip()


def _is_supported_lotus_ai_tenant_id(value: str) -> bool:
    return (
        bool(value)
        and len(value) <= _MAX_LOTUS_AI_TENANT_ID_LENGTH
        and not _has_control_text(value)
    )


def _has_control_text(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)
