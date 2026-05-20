from src.core.proposals.models import ProposalWorkflowState


class ProposalExpectedStateError(ValueError):
    pass


def validate_expected_state(
    *,
    current_state: ProposalWorkflowState,
    expected_state: ProposalWorkflowState | None,
    require_expected_state: bool,
) -> None:
    if expected_state is None and require_expected_state:
        raise ProposalExpectedStateError("STATE_CONFLICT: expected_state is required")
    if expected_state is not None and expected_state != current_state:
        raise ProposalExpectedStateError("STATE_CONFLICT: expected_state mismatch")
