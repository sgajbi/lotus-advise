from collections.abc import Callable
from typing import NoReturn, TypeVar, cast

from fastapi import HTTPException, Request, status

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.sensitive_error_details import contains_sensitive_error_detail
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

_ProposalOperationResult = TypeVar("_ProposalOperationResult")


def run_proposal_operation(
    operation: Callable[[], _ProposalOperationResult],
) -> _ProposalOperationResult:
    try:
        return operation()
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalStateConflictError,
        ProposalTransitionError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


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


def reject_unexpected_query_params(request: Request, *, allowed_params: set[str]) -> None:
    for param_name in request.query_params:
        if param_name not in allowed_params:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail=f"UNSUPPORTED_QUERY_PARAMETER: {param_name} not supported for this endpoint",
            )


def raise_policy_control_http_exception(*, status_code: int, detail: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail)


def raise_proposal_api_http_exception(*, status_code: int, detail: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail=detail)


def safe_proposal_error_detail(error_detail: str, *, redacted_detail: str) -> str:
    if contains_sensitive_proposal_error_detail(error_detail):
        return redacted_detail
    return error_detail


def contains_sensitive_proposal_error_detail(error_detail: str) -> bool:
    return cast(bool, contains_sensitive_error_detail(error_detail))
