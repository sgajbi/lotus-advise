import pytest

from src.core.proposals.concurrency import (
    ProposalExpectedStateError,
    validate_expected_state,
)


def test_validate_expected_state_accepts_matching_state():
    validate_expected_state(
        current_state="DRAFT",
        expected_state="DRAFT",
        require_expected_state=True,
    )


def test_validate_expected_state_allows_missing_optional_state():
    validate_expected_state(
        current_state="DRAFT",
        expected_state=None,
        require_expected_state=False,
    )


def test_validate_expected_state_requires_expected_state_when_configured():
    with pytest.raises(ProposalExpectedStateError) as exc:
        validate_expected_state(
            current_state="DRAFT",
            expected_state=None,
            require_expected_state=True,
        )

    assert str(exc.value) == "STATE_CONFLICT: expected_state is required"


def test_validate_expected_state_rejects_mismatch():
    with pytest.raises(ProposalExpectedStateError) as exc:
        validate_expected_state(
            current_state="DRAFT",
            expected_state="RISK_REVIEW",
            require_expected_state=True,
        )

    assert str(exc.value) == "STATE_CONFLICT: expected_state mismatch"
