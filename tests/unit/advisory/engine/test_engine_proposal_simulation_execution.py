from src.core.models import ProposalSimulateRequest
from src.core.proposals.simulation_execution import run_advisory_proposal_simulation


def _simulate_request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest(
        portfolio_snapshot={
            "portfolio_id": "pf_simulation_execution",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        market_data_snapshot={
            "prices": [
                {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        shelf_entries=[
            {"instrument_id": "EQ_OLD", "status": "APPROVED"},
            {"instrument_id": "EQ_NEW", "status": "APPROVED"},
        ],
        options={"enable_proposal_simulation": True},
        proposed_cash_flows=[{"currency": "USD", "amount": "100"}],
        proposed_trades=[{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
    )


def test_run_advisory_proposal_simulation_resolves_missing_correlation_id(monkeypatch):
    captured = {}
    expected = object()

    def _evaluate_advisory_proposal(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        "src.core.proposals.simulation_execution.evaluate_advisory_proposal",
        _evaluate_advisory_proposal,
    )

    result = run_advisory_proposal_simulation(
        request=_simulate_request(),
        resolved_as_of="2026-05-21",
        request_hash="sha256:simulation-execution",
        idempotency_key="idem-simulation-execution",
        correlation_id=None,
        policy_context={"jurisdiction": "SG"},
    )

    assert result is expected
    assert captured["request_hash"] == "sha256:simulation-execution"
    assert captured["idempotency_key"] == "idem-simulation-execution"
    assert captured["correlation_id"].startswith("corr_")
    assert captured["resolved_as_of"] == "2026-05-21"
    assert captured["policy_context"] == {"jurisdiction": "SG"}


def test_run_advisory_proposal_simulation_preserves_supplied_correlation_id(monkeypatch):
    captured = {}
    expected = object()

    def _evaluate_advisory_proposal(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        "src.core.proposals.simulation_execution.evaluate_advisory_proposal",
        _evaluate_advisory_proposal,
    )

    result = run_advisory_proposal_simulation(
        request=_simulate_request(),
        resolved_as_of="2026-05-21",
        request_hash="sha256:simulation-execution",
        idempotency_key=None,
        correlation_id="corr_supplied",
        policy_context=None,
    )

    assert result is expected
    assert captured["correlation_id"] == "corr_supplied"
