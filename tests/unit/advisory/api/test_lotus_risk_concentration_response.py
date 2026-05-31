from pydantic import ValidationError

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_risk.concentration_response import (
    LotusRiskConcentrationResponse,
    apply_concentration_response,
)


def _request() -> ProposalSimulateRequest:
    return ProposalSimulateRequest.model_validate(
        {
            "portfolio_snapshot": {
                "portfolio_id": "DEMO_ADV_USD_001",
                "base_currency": "USD",
                "positions": [],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
                "fx_rates": [],
            },
            "shelf_entries": [],
            "reference_model": None,
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [],
        }
    )


def _proposal_result() -> ProposalResult:
    request = _request()
    result = run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:risk-response",
        idempotency_key=None,
        correlation_id="corr-risk-response",
        simulation_contract_version="advisory-simulation.v1",
    )
    result.explanation["existing"] = {"preserved": True}
    return result


def _concentration_payload() -> dict:
    return {
        "source_service": "lotus-risk",
        "input_mode": "stateless",
        "risk_proxy": {"hhi_current": "5200.0", "hhi_proposed": "6800.0", "hhi_delta": "1600.0"},
        "single_position_concentration": {
            "top_position_weight_current": "0.5",
            "top_position_weight_proposed": "0.6",
            "top_position_weight_delta": "0.1",
            "top_n_cumulative_weight_current": "0.8",
            "top_n_cumulative_weight_proposed": "0.9",
            "top_n_cumulative_weight_delta": "0.1",
            "top_n": 10,
            "top_position_current": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": "0.5",
            },
            "top_position_proposed": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": "0.6",
            },
        },
        "issuer_concentration": {
            "hhi_current": "5200.0",
            "hhi_proposed": "5800.0",
            "hhi_delta": "600.0",
            "top_issuer_weight_current": "0.5",
            "top_issuer_weight_proposed": "0.6",
            "top_issuer_weight_delta": "0.1",
            "coverage_status": "complete",
            "coverage_ratio_current": "1.0",
            "coverage_ratio_proposed": "1.0",
            "covered_position_count_current": 1,
            "covered_position_count_proposed": 1,
            "total_position_count_current": 1,
            "total_position_count_proposed": 1,
            "uncovered_position_count_current": 0,
            "uncovered_position_count_proposed": 0,
            "top_issuer_current": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": "0.5",
            },
            "top_issuer_proposed": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": "0.6",
            },
        },
        "valuation_context": {"position_basis": "market_value_base"},
        "metadata": {"simulation_session_id": "SIM_RISK_001"},
    }


def test_apply_concentration_response_attaches_canonical_risk_lens() -> None:
    result = _proposal_result()
    concentration = LotusRiskConcentrationResponse.model_validate(_concentration_payload())

    enriched = apply_concentration_response(
        proposal_result=result,
        concentration=concentration,
    )

    assert enriched.explanation["existing"] == {"preserved": True}
    assert enriched.explanation["risk_lens"] == {
        "source_service": "lotus-risk",
        "input_mode": "stateless",
        "risk_proxy": {
            "hhi_current": "5200.0",
            "hhi_proposed": "6800.0",
            "hhi_delta": "1600.0",
        },
        "single_position_concentration": {
            "top_position_weight_current": "0.5",
            "top_position_weight_proposed": "0.6",
            "top_position_weight_delta": "0.1",
            "top_n_cumulative_weight_current": "0.8",
            "top_n_cumulative_weight_proposed": "0.9",
            "top_n_cumulative_weight_delta": "0.1",
            "top_n": 10,
            "top_position_current": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": "0.5",
            },
            "top_position_proposed": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": "0.6",
            },
        },
        "issuer_concentration": {
            "hhi_current": "5200.0",
            "hhi_proposed": "5800.0",
            "hhi_delta": "600.0",
            "top_issuer_weight_current": "0.5",
            "top_issuer_weight_proposed": "0.6",
            "top_issuer_weight_delta": "0.1",
            "coverage_status": "complete",
            "coverage_ratio_current": "1.0",
            "coverage_ratio_proposed": "1.0",
            "covered_position_count_current": 1,
            "covered_position_count_proposed": 1,
            "total_position_count_current": 1,
            "total_position_count_proposed": 1,
            "uncovered_position_count_current": 0,
            "uncovered_position_count_proposed": 0,
            "top_issuer_current": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": "0.5",
            },
            "top_issuer_proposed": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": "0.6",
            },
            "note": None,
        },
        "valuation_context": {"position_basis": "market_value_base"},
        "metadata": {"simulation_session_id": "SIM_RISK_001"},
    }


def test_concentration_response_rejects_wrong_source_service() -> None:
    payload = _concentration_payload()
    payload["source_service"] = "lotus-advise"

    try:
        LotusRiskConcentrationResponse.model_validate(payload)
    except ValidationError as exc:
        assert "source_service" in str(exc)
    else:
        raise AssertionError("invalid source service should fail validation")
