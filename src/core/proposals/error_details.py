from __future__ import annotations

from src.core.common.sensitive_error_details import contains_sensitive_error_detail

PROPOSAL_CONTEXT_RESOLUTION_FAILED_DETAIL = "PROPOSAL_CONTEXT_RESOLUTION_FAILED"


def safe_proposal_error_detail(detail: str, *, fallback: str) -> str:
    if contains_sensitive_error_detail(detail):
        return fallback
    return detail
