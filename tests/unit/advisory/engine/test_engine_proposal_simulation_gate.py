import pytest

from src.core.models import EngineOptions, ProposalSimulateRequest
from src.core.proposals.simulation_gate import (
    PROPOSAL_SIMULATION_DISABLED_MESSAGE,
    ProposalSimulationGateError,
    validate_proposal_simulation_enabled,
)


def _request(*, enable_proposal_simulation: bool) -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot={
            "portfolio_id": "pf_simulation_gate",
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


def test_validate_proposal_simulation_enabled_accepts_enabled_request():
    validate_proposal_simulation_enabled(
        request=_request(enable_proposal_simulation=True),
    )


def test_validate_proposal_simulation_enabled_rejects_disabled_request():
    with pytest.raises(ProposalSimulationGateError) as exc:
        validate_proposal_simulation_enabled(
            request=_request(enable_proposal_simulation=False),
        )

    assert str(exc.value) == PROPOSAL_SIMULATION_DISABLED_MESSAGE


def test_validate_proposal_simulation_enabled_allows_disabled_request_when_not_required():
    validate_proposal_simulation_enabled(
        request=_request(enable_proposal_simulation=False),
        require_simulation_flag=False,
    )
