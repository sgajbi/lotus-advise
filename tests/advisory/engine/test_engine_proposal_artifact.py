from src.core.advisory.artifact import build_proposal_artifact
from src.core.advisory_engine import run_proposal_simulation
from src.core.models import EngineOptions, ProposalSimulateRequest


def _build_request(options: EngineOptions | None = None) -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot={
            "portfolio_id": "pf_artifact_1",
            "base_currency": "SGD",
            "positions": [{"instrument_id": "SG_BOND", "quantity": "100"}],
            "cash_balances": [{"currency": "SGD", "amount": "5000"}],
        },
        market_data_snapshot={
            "prices": [
                {"instrument_id": "SG_BOND", "price": "100", "currency": "SGD"},
                {"instrument_id": "US_EQ", "price": "100", "currency": "USD"},
            ],
            "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
        },
        shelf_entries=[
            {"instrument_id": "SG_BOND", "status": "APPROVED", "asset_class": "BOND"},
            {"instrument_id": "US_EQ", "status": "APPROVED", "asset_class": "EQUITY"},
        ],
        options=options or {"enable_proposal_simulation": True},
        proposed_cash_flows=[{"currency": "SGD", "amount": "1000"}],
        proposed_trades=[{"side": "BUY", "instrument_id": "US_EQ", "quantity": "10"}],
    )


def _simulate(request: ProposalSimulateRequest, request_hash: str):
    return run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash=request_hash,
        idempotency_key="artifact-idem",
        correlation_id="corr-artifact",
    )


def test_proposal_artifact_hash_is_deterministic_when_created_at_differs():
    request = _build_request()
    result = _simulate(request, "sha256:artifact-deterministic")

    artifact_one = build_proposal_artifact(
        request=request,
        proposal_result=result,
        created_at="2026-02-19T00:00:00+00:00",
    )
    artifact_two = build_proposal_artifact(
        request=request,
        proposal_result=result,
        created_at="2026-02-19T00:05:00+00:00",
    )

    assert artifact_one.created_at != artifact_two.created_at
    assert (
        artifact_one.evidence_bundle.hashes.artifact_hash
        == artifact_two.evidence_bundle.hashes.artifact_hash
    )


def test_proposal_artifact_contains_trade_dependencies_and_sorted_weight_changes():
    request = _build_request()
    result = _simulate(request, "sha256:artifact-content")
    artifact = build_proposal_artifact(request=request, proposal_result=result)

    assert artifact.trades_and_funding.trade_list[0].instrument_id == "US_EQ"
    assert artifact.trades_and_funding.trade_list[0].dependencies == ["oi_fx_1"]
    assert artifact.portfolio_impact.delta.largest_weight_changes
    assert artifact.portfolio_impact.delta.largest_weight_changes[0].bucket_id == "US_EQ"


def test_proposal_artifact_marks_suitability_not_available_when_disabled():
    request = _build_request(
        options=EngineOptions(
            enable_proposal_simulation=True,
            enable_suitability_scanner=False,
        )
    )
    result = _simulate(request, "sha256:artifact-no-suitability")
    artifact = build_proposal_artifact(request=request, proposal_result=result)

    assert artifact.suitability_summary.status == "NOT_AVAILABLE"
    assert artifact.suitability_summary.new_issues == 0
