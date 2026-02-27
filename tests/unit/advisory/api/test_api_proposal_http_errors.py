import pytest
from fastapi import HTTPException

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.routers.proposal_http_errors import raise_proposal_http_exception
from src.core.proposals import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (ProposalNotFoundError("missing"), 404),
        (ProposalIdempotencyConflictError("idem"), 409),
        (ProposalStateConflictError("state"), 409),
        (ProposalTransitionError("transition"), HTTP_422_UNPROCESSABLE),
        (ProposalValidationError("validation"), HTTP_422_UNPROCESSABLE),
    ],
)
def test_raise_proposal_http_exception_maps_domain_errors(
    exc: Exception, expected_status: int
) -> None:
    with pytest.raises(HTTPException) as caught:
        raise_proposal_http_exception(exc)
    assert caught.value.status_code == expected_status
    assert caught.value.detail == str(exc)


def test_raise_proposal_http_exception_reraises_unknown_error() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        raise_proposal_http_exception(RuntimeError("boom"))
