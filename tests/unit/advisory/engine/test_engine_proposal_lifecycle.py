import pytest

from src.core.proposals.lifecycle import (
    ProposalLifecycleOriginError,
    validate_lifecycle_origin,
)


@pytest.mark.parametrize(
    ("lifecycle_origin", "source_workspace_id"),
    [
        ("DIRECT_CREATE", None),
        ("WORKSPACE_HANDOFF", "aws_lifecycle_origin"),
    ],
)
def test_validate_lifecycle_origin_accepts_valid_entry_points(
    lifecycle_origin,
    source_workspace_id,
):
    validate_lifecycle_origin(
        lifecycle_origin=lifecycle_origin,
        source_workspace_id=source_workspace_id,
    )


def test_validate_lifecycle_origin_requires_workspace_for_handoff():
    with pytest.raises(ProposalLifecycleOriginError) as exc:
        validate_lifecycle_origin(
            lifecycle_origin="WORKSPACE_HANDOFF",
            source_workspace_id=None,
        )

    assert str(exc.value) == "WORKSPACE_HANDOFF_SOURCE_WORKSPACE_ID_REQUIRED"


def test_validate_lifecycle_origin_rejects_workspace_for_direct_create():
    with pytest.raises(ProposalLifecycleOriginError) as exc:
        validate_lifecycle_origin(
            lifecycle_origin="DIRECT_CREATE",
            source_workspace_id="aws_direct_create",
        )

    assert str(exc.value) == "DIRECT_CREATE_CANNOT_INCLUDE_SOURCE_WORKSPACE_ID"
