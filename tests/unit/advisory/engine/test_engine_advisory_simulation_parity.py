import pytest

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalSimulateRequest
from tests.shared.advisory_simulation_parity import (
    iter_parity_scenarios,
    normalize_result_for_parity,
)


@pytest.mark.parametrize(
    ("scenario_name", "request_hash", "payload", "expected"),
    [
        (
            scenario["name"],
            scenario["request_hash"],
            scenario["payload"],
            scenario["expected"],
        )
        for scenario in iter_parity_scenarios()
    ],
    ids=[scenario["name"] for scenario in iter_parity_scenarios()],
)
def test_local_advisory_engine_matches_curated_parity_scenarios(
    scenario_name: str,
    request_hash: str,
    payload: dict,
    expected: dict,
) -> None:
    request = ProposalSimulateRequest.model_validate(payload)

    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        simulation_contract_version="advisory-simulation.v1",
    )

    assert normalize_result_for_parity(result) == expected, scenario_name
