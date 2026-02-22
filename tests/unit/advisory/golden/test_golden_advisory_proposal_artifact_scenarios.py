import json
import os
from decimal import Decimal

import pytest

from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalSimulateRequest


def _load_golden(path):
    with open(path, "r") as file:
        return json.loads(file.read(), parse_float=Decimal)


@pytest.mark.parametrize(
    "filename",
    [
        "scenario_14E_artifact_basic.json",
        "scenario_14E_artifact_with_fx.json",
        "scenario_14E_artifact_with_suitability.json",
    ],
)
def test_golden_advisory_proposal_artifact_scenarios(filename):
    path = os.path.join(os.path.dirname(__file__), "../golden_data", filename)
    data = _load_golden(path)
    request = ProposalSimulateRequest.model_validate(data["proposal_inputs"])

    proposal_result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:golden-14e",
        idempotency_key=f"golden-{filename}",
        correlation_id=f"corr-{filename}",
    )
    artifact = build_proposal_artifact(request=request, proposal_result=proposal_result)
    expected = data["expected_artifact_output"]

    assert artifact.status == expected["status"]
    assert artifact.summary.recommended_next_step == expected["recommended_next_step"]
    assert artifact.summary.objective_tags == expected["objective_tags"]
    assert [trade.instrument_id for trade in artifact.trades_and_funding.trade_list] == expected[
        "trade_instruments"
    ]
    assert [fx.pair for fx in artifact.trades_and_funding.fx_list] == expected["fx_pairs"]
    assert artifact.suitability_summary.status == expected["suitability_status"]

    again = build_proposal_artifact(request=request, proposal_result=proposal_result)
    assert (
        artifact.evidence_bundle.hashes.artifact_hash == again.evidence_bundle.hashes.artifact_hash
    )
