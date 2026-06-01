from collections.abc import Callable
from typing import NoReturn, TypeVar

from fastapi import HTTPException, status

from src.api.proposals.errors import safe_proposal_error_detail
from src.integrations.lotus_report import LotusReportUnavailableError

LOTUS_REPORT_REQUEST_UNAVAILABLE_DETAIL = "LOTUS_REPORT_REQUEST_UNAVAILABLE"

_LotusReportOperationResult = TypeVar("_LotusReportOperationResult")


def run_lotus_report_operation(
    operation: Callable[[], _LotusReportOperationResult],
) -> _LotusReportOperationResult:
    try:
        return operation()
    except LotusReportUnavailableError as exc:
        raise_lotus_report_unavailable_http_exception(exc)


def raise_lotus_report_unavailable_http_exception(exc: Exception) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=safe_proposal_error_detail(
            str(exc),
            redacted_detail=LOTUS_REPORT_REQUEST_UNAVAILABLE_DETAIL,
        ),
    ) from exc
