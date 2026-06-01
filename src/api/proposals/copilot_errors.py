from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.sensitive_error_details import contains_sensitive_error_detail

ADVISORY_COPILOT_RESPONSES = {
    status.HTTP_404_NOT_FOUND: {"description": "Copilot evidence packet or run was not found."},
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key or evidence-packet identifier conflicts with prior data."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Copilot request failed validation or guardrail-safe persistence checks."
    },
}

COPILOT_REPOSITORY_UNAVAILABLE_DETAIL = "ADVISORY_COPILOT_REPOSITORY_UNAVAILABLE"
COPILOT_VALIDATION_FAILED_DETAIL = "ADVISORY_COPILOT_REQUEST_VALIDATION_FAILED"


def raise_copilot_http_exception(exc: ValueError) -> NoReturn:
    detail = safe_copilot_error_detail(str(exc))
    if detail.endswith("_NOT_FOUND"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if "CONFLICT" in detail or "TERMINAL" in detail:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=HTTP_422_UNPROCESSABLE, detail=detail) from exc


def safe_copilot_error_detail(error_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return COPILOT_VALIDATION_FAILED_DETAIL
    return error_detail


def safe_copilot_repository_error_detail(error_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return COPILOT_REPOSITORY_UNAVAILABLE_DETAIL
    return error_detail
