from typing import NoReturn

from fastapi import HTTPException, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)

PROPOSAL_NOT_FOUND_DETAIL = "PROPOSAL_NOT_FOUND"
PROPOSAL_CONFLICT_DETAIL = "PROPOSAL_CONFLICT"
PROPOSAL_REQUEST_VALIDATION_FAILED_DETAIL = "PROPOSAL_REQUEST_VALIDATION_FAILED"
_PROPOSAL_SENSITIVE_ERROR_FRAGMENTS = (
    "authorization",
    "bearer ",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "raw prompt",
    "raw payload",
    "raw source",
    "provider response",
)


def raise_proposal_http_exception(exc: Exception) -> NoReturn:
    if isinstance(exc, ProposalNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=safe_proposal_error_detail(
                str(exc),
                redacted_detail=PROPOSAL_NOT_FOUND_DETAIL,
            ),
        ) from exc
    if isinstance(exc, (ProposalIdempotencyConflictError, ProposalStateConflictError)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=safe_proposal_error_detail(
                str(exc),
                redacted_detail=PROPOSAL_CONFLICT_DETAIL,
            ),
        ) from exc
    if isinstance(exc, (ProposalTransitionError, ProposalValidationError)):
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail=safe_proposal_error_detail(
                str(exc),
                redacted_detail=PROPOSAL_REQUEST_VALIDATION_FAILED_DETAIL,
            ),
        ) from exc
    raise exc


def safe_proposal_error_detail(error_detail: str, *, redacted_detail: str) -> str:
    if contains_sensitive_proposal_error_detail(error_detail):
        return redacted_detail
    return error_detail


def contains_sensitive_proposal_error_detail(error_detail: str) -> bool:
    normalized = error_detail.lower().replace("-", " ").replace("_", " ")
    return any(
        fragment.replace("-", " ").replace("_", " ") in normalized
        for fragment in _PROPOSAL_SENSITIVE_ERROR_FRAGMENTS
    )
