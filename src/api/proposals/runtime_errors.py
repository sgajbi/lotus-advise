from __future__ import annotations

from fastapi import HTTPException, status

from src.api.routers.runtime_utils import normalize_backend_init_error

PROPOSAL_POSTGRES_DSN_REQUIRED_DETAIL = "PROPOSAL_POSTGRES_DSN_REQUIRED"
PROPOSAL_POSTGRES_CONNECTION_FAILED_DETAIL = "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def proposal_backend_init_error_detail(detail: str) -> str:
    return normalize_backend_init_error(
        detail=detail,
        required_detail=PROPOSAL_POSTGRES_DSN_REQUIRED_DETAIL,
        fallback_detail=PROPOSAL_POSTGRES_CONNECTION_FAILED_DETAIL,
    )


def proposal_backend_unavailable_exception(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=proposal_backend_init_error_detail(detail),
    )


def proposal_backend_connection_failed_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=PROPOSAL_POSTGRES_CONNECTION_FAILED_DETAIL,
    )
