from typing import Any

import httpx
import pytest

from src.core.advisory_engine import run_proposal_simulation
from src.core.models import ProposalResult, ProposalSimulateRequest
from src.integrations.lotus_risk.enrichment import (
    LotusRiskEnrichmentUnavailableError,
    enrich_with_lotus_risk,
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
            "shelf_entries": [
                {
                    "instrument_id": "EQ_1",
                    "status": "APPROVED",
                    "issuer_id": "ISSUER_1",
                    "attributes": {"ultimate_parent_issuer_id": "PARENT_1"},
                }
            ],
            "reference_model": {
                "model_id": "MODEL_1",
                "as_of": "2026-03-25",
                "base_currency": "USD",
                "asset_class_targets": [],
            },
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"}],
        }
    )


def _proposal_result(request: ProposalSimulateRequest) -> ProposalResult:
    return run_proposal_simulation(
        portfolio=request.portfolio_snapshot,
        market_data=request.market_data_snapshot,
        shelf=request.shelf_entries,
        options=request.options,
        proposed_cash_flows=request.proposed_cash_flows,
        proposed_trades=request.proposed_trades,
        reference_model=request.reference_model,
        request_hash="sha256:risk-client",
        idempotency_key=None,
        correlation_id="corr-risk-client",
        simulation_contract_version="advisory-simulation.v1",
    )


def _risk_response_payload() -> dict[str, Any]:
    return {
        "source_service": "lotus-risk",
        "input_mode": "simulation",
        "risk_proxy": {"hhi_current": 5200.0, "hhi_proposed": 6800.0, "hhi_delta": 1600.0},
        "single_position_concentration": {
            "top_position_weight_current": 0.5,
            "top_position_weight_proposed": 0.6,
            "top_position_weight_delta": 0.1,
            "top_n_cumulative_weight_current": 0.8,
            "top_n_cumulative_weight_proposed": 0.9,
            "top_n_cumulative_weight_delta": 0.1,
            "top_n": 10,
        },
        "issuer_concentration": {
            "hhi_current": 5200.0,
            "hhi_proposed": 5800.0,
            "hhi_delta": 600.0,
            "top_issuer_weight_current": 0.5,
            "top_issuer_weight_proposed": 0.6,
            "top_issuer_weight_delta": 0.1,
            "coverage_status": "complete",
            "covered_position_count_current": 1,
            "covered_position_count_proposed": 1,
            "total_position_count_current": 1,
            "total_position_count_proposed": 1,
            "note": None,
        },
        "valuation_context": {
            "portfolio_currency": "USD",
            "reporting_currency": "USD",
            "position_basis": "market_value_base",
            "weight_basis": "total_market_value_base",
        },
        "metadata": {
            "portfolio_id": "DEMO_ADV_USD_001",
            "as_of_date": "2026-03-25",
            "simulation_session_id": "SIM_RISK_001",
            "simulation_session_version": 2,
        },
    }


class _FakeResponse:
    def __init__(self, *, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://lotus-risk/analytics/risk/concentration")
            response = httpx.Response(self.status_code, json=self._payload, request=request)
            raise httpx.HTTPStatusError("upstream risk error", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.response


def test_enrich_with_lotus_risk_maps_proposal_to_simulation_concentration(monkeypatch):
    request = _request()
    result = _proposal_result(request)
    fake_client = _FakeClient(_FakeResponse(status_code=200, payload=_risk_response_payload()))
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.lotus_risk.enrichment.httpx.Client",
        lambda timeout: fake_client,
    )

    enriched = enrich_with_lotus_risk(
        request=request,
        proposal_result=result,
        correlation_id="corr-risk-client",
    )

    call = fake_client.calls[0]
    payload = call["json"]
    simulation_input = payload["simulation_input"]
    assert call["url"] == "http://lotus-risk:8130/analytics/risk/concentration"
    assert call["headers"]["X-Correlation-Id"] == "corr-risk-client"
    assert payload["input_mode"] == "simulation"
    assert payload["issuer_grouping_level"] == "ultimate_parent"
    assert simulation_input["portfolio_id"] == "DEMO_ADV_USD_001"
    assert simulation_input["as_of_date"] == "2026-03-25"
    assert simulation_input["reporting_currency"] == "USD"
    assert simulation_input["simulation_changes"] == [
        {
            "security_id": "EQ_1",
            "transaction_type": "BUY",
            "quantity": 2.0,
            "amount": 200.0,
            "currency": "USD",
            "metadata": {
                "proposal_intent_id": "oi_1",
                "proposal_intent_type": "SECURITY_TRADE",
            },
        }
    ]
    assert simulation_input["issuer_mappings"] == [
        {
            "security_id": "EQ_1",
            "issuer_id": "ISSUER_1",
            "ultimate_parent_issuer_id": "PARENT_1",
        }
    ]
    assert enriched.explanation["risk_lens"]["source_service"] == "lotus-risk"
    assert enriched.explanation["risk_lens"]["risk_proxy"]["hhi_delta"] == 1600.0


def test_enrich_with_lotus_risk_requires_configured_base_url(monkeypatch):
    monkeypatch.delenv("LOTUS_RISK_BASE_URL", raising=False)
    request = _request()

    with pytest.raises(LotusRiskEnrichmentUnavailableError):
        enrich_with_lotus_risk(
            request=request,
            proposal_result=_proposal_result(request),
            correlation_id="corr-risk-client",
        )


def test_enrich_with_lotus_risk_rejects_upstream_http_failure(monkeypatch):
    request = _request()
    fake_client = _FakeClient(_FakeResponse(status_code=503, payload={"detail": "unavailable"}))
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.lotus_risk.enrichment.httpx.Client",
        lambda timeout: fake_client,
    )

    with pytest.raises(LotusRiskEnrichmentUnavailableError):
        enrich_with_lotus_risk(
            request=request,
            proposal_result=_proposal_result(request),
            correlation_id="corr-risk-client",
        )


def test_enrich_with_lotus_risk_rejects_contract_mismatch(monkeypatch):
    request = _request()
    payload = _risk_response_payload()
    payload["input_mode"] = "stateful"
    fake_client = _FakeClient(_FakeResponse(status_code=200, payload=payload))
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.lotus_risk.enrichment.httpx.Client",
        lambda timeout: fake_client,
    )

    with pytest.raises(LotusRiskEnrichmentUnavailableError):
        enrich_with_lotus_risk(
            request=request,
            proposal_result=_proposal_result(request),
            correlation_id="corr-risk-client",
        )


def test_enrich_with_lotus_risk_prefers_resolved_as_of_for_stateful_context(monkeypatch):
    request = _request()
    request.reference_model = None
    fake_client = _FakeClient(_FakeResponse(status_code=200, payload=_risk_response_payload()))
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.lotus_risk.enrichment.httpx.Client",
        lambda timeout: fake_client,
    )

    enrich_with_lotus_risk(
        request=request,
        proposal_result=_proposal_result(_request()),
        correlation_id="corr-risk-client",
        resolved_as_of="2026-03-27",
    )

    assert fake_client.calls[0]["json"]["simulation_input"]["as_of_date"] == "2026-03-27"
