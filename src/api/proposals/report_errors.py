from typing import NoReturn

from fastapi import HTTPException, status

from src.api.proposals.errors import safe_proposal_error_detail

LOTUS_REPORT_REQUEST_UNAVAILABLE_DETAIL = "LOTUS_REPORT_REQUEST_UNAVAILABLE"


def raise_lotus_report_unavailable_http_exception(exc: Exception) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=safe_proposal_error_detail(
            str(exc),
            redacted_detail=LOTUS_REPORT_REQUEST_UNAVAILABLE_DETAIL,
        ),
    ) from exc
