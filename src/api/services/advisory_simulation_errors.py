from __future__ import annotations

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.proposals.errors import (
    PROPOSAL_REQUEST_VALIDATION_FAILED_DETAIL,
    safe_proposal_error_detail,
)


def safe_simulation_validation_detail(error_detail: str) -> str:
    return safe_proposal_error_detail(
        error_detail,
        redacted_detail=PROPOSAL_REQUEST_VALIDATION_FAILED_DETAIL,
    )


def simulation_validation_exception(error_detail: str) -> HTTPException:
    return HTTPException(
        status_code=HTTP_422_UNPROCESSABLE,
        detail=safe_simulation_validation_detail(error_detail),
    )


def simulation_idempotency_conflict_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="IDEMPOTENCY_KEY_CONFLICT: request hash mismatch",
    )


def simulation_idempotency_store_unavailable_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="PROPOSAL_IDEMPOTENCY_STORE_WRITE_FAILED",
    )
