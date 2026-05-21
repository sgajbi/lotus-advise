import pytest

from src.core.models import EngineOptions, ProposalSimulateRequest
from src.core.proposals.command_validation import (
    resolve_proposal_approval_transition,
    resolve_proposal_transition_state,
    validate_proposal_expected_state,
    validate_proposal_simulation_flag,
)
from src.core.proposals.exceptions import (
    ProposalStateConflictError,
    ProposalTransitionError,
    ProposalValidationError,
)


def _request(*, enable_proposal_simulation: bool) -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot={
            "portfolio_id": "pf_command_validation",
            "base_currency": "USD",
            "positions": [],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        market_data_snapshot={"prices": [], "fx_rates": []},
        shelf_entries=[],
        proposed_trades=[],
        proposed_cash_flows=[],
        options=EngineOptions(enable_proposal_simulation=enable_proposal_simulation),
    )


def test_validate_proposal_simulation_flag_maps_gate_errors_to_validation_errors():
    with pytest.raises(ProposalValidationError) as exc:
        validate_proposal_simulation_flag(
            request=_request(enable_proposal_simulation=False),
            require_simulation_flag=True,
        )

    assert "PROPOSAL_SIMULATION_DISABLED" in str(exc.value)


def test_validate_proposal_expected_state_maps_state_conflicts():
    with pytest.raises(ProposalStateConflictError) as exc:
        validate_proposal_expected_state(
            current_state="DRAFT",
            expected_state="RISK_REVIEW",
            require_expected_state=True,
        )

    assert str(exc.value) == "STATE_CONFLICT: expected_state mismatch"


def test_resolve_proposal_transition_state_maps_rule_errors():
    with pytest.raises(ProposalTransitionError) as exc:
        resolve_proposal_transition_state(
            current_state="DRAFT",
            event_type="EXECUTION_REQUESTED",
        )

    assert str(exc.value) == "INVALID_TRANSITION"


def test_resolve_proposal_approval_transition_maps_rule_errors():
    with pytest.raises(ProposalTransitionError) as exc:
        resolve_proposal_approval_transition(
            current_state="DRAFT",
            approval_type="UNKNOWN",
            approved=True,
        )

    assert str(exc.value) == "INVALID_APPROVAL_TYPE"
