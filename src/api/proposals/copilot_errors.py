from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn, TypeVar

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.sensitive_error_details import contains_sensitive_error_detail

ADVISORY_COPILOT_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {
        "description": "A complete, active Advisory Copilot caller principal is required."
    },
    status.HTTP_403_FORBIDDEN: {
        "description": "The caller principal is not authorized for the requested Copilot resource."
    },
    status.HTTP_404_NOT_FOUND: {"description": "Copilot evidence packet or run was not found."},
    status.HTTP_409_CONFLICT: {
        "description": "Idempotency key or evidence-packet identifier conflicts with prior data."
    },
    HTTP_422_UNPROCESSABLE: {
        "description": "Copilot request failed validation or guardrail-safe persistence checks."
    },
}

ADVISORY_COPILOT_SUPPORTABILITY_RESPONSES = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Advisory copilot supportability posture could not be assembled."
    },
}

COPILOT_REPOSITORY_UNAVAILABLE_DETAIL = "ADVISORY_COPILOT_REPOSITORY_UNAVAILABLE"
COPILOT_VALIDATION_FAILED_DETAIL = "ADVISORY_COPILOT_REQUEST_VALIDATION_FAILED"

_UNAUTHENTICATED_PRINCIPAL_SUFFIXES = ("_PRINCIPAL_REQUIRED", "_PRINCIPAL_INVALID")
_FORBIDDEN_PRINCIPAL_SUFFIXES = (
    "_ROLE_NOT_AUTHORIZED",
    "_CAPABILITY_REQUIRED",
    "_SCOPE_REQUIRED",
    "_SCOPE_FORBIDDEN",
)

_CopilotOperationResult = TypeVar("_CopilotOperationResult")


def run_copilot_operation(
    operation: Callable[[], _CopilotOperationResult],
) -> _CopilotOperationResult:
    try:
        return operation()
    except ValueError as exc:
        raise_copilot_http_exception(exc)


def raise_copilot_http_exception(exc: ValueError) -> NoReturn:
    detail = safe_copilot_error_detail(str(exc))
    if detail.endswith(_UNAUTHENTICATED_PRINCIPAL_SUFFIXES):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail) from exc
    if is_copilot_forbidden_detail(detail):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
    if detail.endswith("_NOT_FOUND"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
    if "CONFLICT" in detail or "TERMINAL" in detail:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    raise HTTPException(status_code=HTTP_422_UNPROCESSABLE, detail=detail) from exc


def is_copilot_forbidden_detail(detail: str) -> bool:
    return detail.endswith(_FORBIDDEN_PRINCIPAL_SUFFIXES) or (
        detail == "COPILOT_CALLER_ACTOR_MISMATCH"
    )


def safe_copilot_error_detail(error_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return COPILOT_VALIDATION_FAILED_DETAIL
    return error_detail


def safe_copilot_repository_error_detail(error_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return COPILOT_REPOSITORY_UNAVAILABLE_DETAIL
    return error_detail


def copilot_repository_unavailable_exception(error_detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=safe_copilot_repository_error_detail(error_detail),
    )
