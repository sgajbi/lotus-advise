from typing import cast

from src.core.proposal_request_models import ProposalSimulateRequest
from src.core.proposals.concurrency import (
    ProposalExpectedStateError,
    validate_expected_state,
)
from src.core.proposals.exceptions import (
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)
from src.core.proposals.models import ProposalWorkflowState
from src.core.proposals.simulation_gate import (
    ProposalSimulationGateError,
    validate_proposal_simulation_enabled,
)
from src.core.proposals.workflow_rules import ProposalWorkflowRuleError
from src.core.proposals.workflow_rules import (
    resolve_approval_transition as build_approval_transition,
)
from src.core.proposals.workflow_rules import (
    resolve_transition_state as build_transition_state,
)


def validate_proposal_simulation_flag(
    *,
    request: ProposalSimulateRequest,
    require_simulation_flag: bool,
) -> None:
    try:
        validate_proposal_simulation_enabled(
            request=request,
            require_simulation_flag=require_simulation_flag,
        )
    except ProposalSimulationGateError as exc:
        raise ProposalValidationError(str(exc)) from exc


def validate_proposal_expected_state(
    *,
    current_state: ProposalWorkflowState,
    expected_state: ProposalWorkflowState | None,
    require_expected_state: bool,
) -> None:
    try:
        validate_expected_state(
            current_state=current_state,
            expected_state=expected_state,
            require_expected_state=require_expected_state,
        )
    except ProposalExpectedStateError as exc:
        raise ProposalStateConflictError(str(exc)) from exc


def resolve_proposal_transition_state(
    *,
    current_state: ProposalWorkflowState,
    event_type: str,
) -> ProposalWorkflowState:
    try:
        return build_transition_state(current_state=current_state, event_type=event_type)
    except ProposalWorkflowRuleError as exc:
        raise ProposalTransitionError(str(exc)) from exc


def resolve_proposal_approval_transition(
    *,
    current_state: ProposalWorkflowState,
    approval_type: str,
    approved: bool,
) -> tuple[str, ProposalWorkflowState]:
    try:
        return cast(
            tuple[str, ProposalWorkflowState],
            build_approval_transition(
                current_state=current_state,
                approval_type=approval_type,
                approved=approved,
            ),
        )
    except ProposalWorkflowRuleError as exc:
        raise ProposalTransitionError(str(exc)) from exc
