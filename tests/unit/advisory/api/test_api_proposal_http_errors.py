import pytest
from fastapi import HTTPException

from src.api.http_status import HTTP_422_UNPROCESSABLE
from src.api.proposals.errors import raise_proposal_http_exception
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


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_detail"),
    [
        (
            ProposalNotFoundError("PROPOSAL_NOT_FOUND token=should-not-leak"),
            404,
            "PROPOSAL_NOT_FOUND",
        ),
        (
            ProposalIdempotencyConflictError("IDEMPOTENCY_CONFLICT raw prompt leaked"),
            409,
            "PROPOSAL_CONFLICT",
        ),
        (
            ProposalStateConflictError("STATE_CONFLICT provider_response leaked"),
            409,
            "PROPOSAL_CONFLICT",
        ),
        (
            ProposalTransitionError("TRANSITION_INVALID secret leaked"),
            HTTP_422_UNPROCESSABLE,
            "PROPOSAL_REQUEST_VALIDATION_FAILED",
        ),
        (
            ProposalValidationError("VALIDATION_INVALID api_key leaked"),
            HTTP_422_UNPROCESSABLE,
            "PROPOSAL_REQUEST_VALIDATION_FAILED",
        ),
    ],
)
def test_raise_proposal_http_exception_redacts_sensitive_detail(
    exc: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    with pytest.raises(HTTPException) as caught:
        raise_proposal_http_exception(exc)

    assert caught.value.status_code == expected_status
    assert caught.value.detail == expected_detail
    detail_text = repr(caught.value.detail).lower()
    assert "should-not-leak" not in detail_text
    assert "raw prompt" not in detail_text
    assert "provider_response" not in detail_text
    assert "secret" not in detail_text
    assert "api_key" not in detail_text
