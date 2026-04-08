from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.core.advisory_engine import run_proposal_simulation
from src.integrations.lotus_core import LotusCoreSimulationUnavailableError
from src.integrations.lotus_core.stateful_context import (
    get_stateful_context_fetch_stats_for_tests,
    reset_stateful_context_cache_for_tests,
)
from src.integrations.lotus_risk import LotusRiskEnrichmentUnavailableError
from tests.shared.lotus_core_query_fakes import (
    CountingLotusCoreQueryClient,
    build_basic_stateful_query_responses,
)
from tests.shared.stateful_context_assertions import assert_core_context_fetch_counts
from tests.shared.stateful_context_builders import build_resolved_stateful_context


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    reset_proposal_workflow_service_for_tests()
    reset_stateful_context_cache_for_tests()
    yield
    app.dependency_overrides = original_overrides
    reset_proposal_workflow_service_for_tests()
    reset_stateful_context_cache_for_tests()


@pytest.fixture(autouse=True)
def stub_core_simulation_authority(monkeypatch):
    def _simulate_with_lotus_core(**kwargs):
        request = kwargs["request"]
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
            simulation_contract_version="advisory-simulation.v1",
        )

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _base_simulation_payload(portfolio_id: str = "pf_prop_api_1") -> dict:
    return {
        "portfolio_snapshot": {
            "portfolio_id": portfolio_id,
            "base_currency": "USD",
            "positions": [],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [{"currency": "USD", "amount": "200"}],
        "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "2"}],
    }


def _resolved_stateful_context(portfolio_id: str, as_of: str) -> dict:
    return build_resolved_stateful_context(
        portfolio_id,
        as_of,
        prices=[{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
        shelf_entries=[{"instrument_id": "EQ_1", "status": "APPROVED"}],
    )


class _FakeRiskResponse:
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


class _FakeRiskClient:
    def __init__(self, response: _FakeRiskResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeRiskClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, *, json: dict[str, Any], headers: dict[str, str]) -> _FakeRiskResponse:
        return self.response


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
            "top_position_current": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": 0.5,
            },
            "top_position_proposed": {
                "security_id": "EQ_1",
                "security_name": "Security 1",
                "weight": 0.6,
            },
        },
        "issuer_concentration": {
            "hhi_current": 5200.0,
            "hhi_proposed": 5800.0,
            "hhi_delta": 600.0,
            "top_issuer_weight_current": 0.5,
            "top_issuer_weight_proposed": 0.6,
            "top_issuer_weight_delta": 0.1,
            "coverage_status": "complete",
            "coverage_ratio_current": 1.0,
            "coverage_ratio_proposed": 1.0,
            "covered_position_count_current": 1,
            "covered_position_count_proposed": 1,
            "total_position_count_current": 1,
            "total_position_count_proposed": 1,
            "uncovered_position_count_current": 0,
            "uncovered_position_count_proposed": 0,
            "top_issuer_current": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": 0.5,
            },
            "top_issuer_proposed": {
                "issuer_id": "PARENT_1",
                "issuer_name": "Parent 1",
                "weight": 0.6,
            },
        },
    }


def test_advisory_proposal_simulate_endpoint_success(client):
    payload = _base_simulation_payload()

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["proposal_run_id"].startswith("pr_")
    assert body["status"] == "READY"
    assert body["intents"][0]["intent_type"] == "CASH_FLOW"
    assert body["correlation_id"].startswith("corr_")
    assert body["suitability"]["recommended_gate"] in {
        "NONE",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
    }
    assert body["gate_decision"]["gate"] in {
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "CLIENT_CONSENT_REQUIRED",
        "EXECUTION_READY",
    }
    assert body["explanation"]["context_resolution"]["input_mode"] == "stateless"
    assert body["explanation"]["context_resolution"]["resolution_source"] == "DIRECT_REQUEST"
    assert body["explanation"]["context_resolution"]["used_legacy_contract"] is True


def test_advisory_proposal_simulate_requires_feature_flag(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_2", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-2"},
    )
    assert response.status_code == 422
    assert "PROPOSAL_SIMULATION_DISABLED" in response.json()["detail"]


def test_advisory_proposal_simulate_supports_stateful_context_resolution(client, monkeypatch):
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
    payload = {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_prop_api_stateful",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_stateful_001",
        },
    }

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-stateful"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lineage"]["portfolio_snapshot_id"] == "ps_pf_prop_api_stateful_2026-03-25"
    assert body["lineage"]["market_data_snapshot_id"] == "md_2026-03-25"
    assert body["explanation"]["context_resolution"]["input_mode"] == "stateful"
    assert body["explanation"]["context_resolution"]["resolution_source"] == "LOTUS_CORE"
    assert body["explanation"]["context_resolution"]["used_legacy_contract"] is False


def test_advisory_proposal_simulate_rejects_stateful_request_when_resolution_unavailable(client):
    response = client.post(
        "/advisory/proposals/simulate",
        json={
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": "pf_prop_api_stateful_missing",
                "as_of": "2026-03-25",
            },
        },
        headers={"Idempotency-Key": "prop-key-stateful-missing"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE"


def test_advisory_proposal_simulate_normalized_stateless_contract_matches_legacy_payload(client):
    legacy_payload = _base_simulation_payload(portfolio_id="pf_prop_api_equivalent")
    normalized_payload = {
        "input_mode": "stateless",
        "stateless_input": {
            "simulate_request": _base_simulation_payload(portfolio_id="pf_prop_api_equivalent")
        },
    }
    headers = {"Idempotency-Key": "prop-key-equivalent"}

    first = client.post("/advisory/proposals/simulate", json=legacy_payload, headers=headers)
    second = client.post("/advisory/proposals/simulate", json=normalized_payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_advisory_proposal_simulate_idempotency_conflict_returns_409(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_3", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }
    headers = {"Idempotency-Key": "prop-key-3"}

    first = client.post("/advisory/proposals/simulate", json=payload, headers=headers)
    assert first.status_code == 200

    payload["proposed_cash_flows"] = [{"currency": "USD", "amount": "1"}]
    second = client.post("/advisory/proposals/simulate", json=payload, headers=headers)
    assert second.status_code == 409
    assert "IDEMPOTENCY_KEY_CONFLICT" in second.json()["detail"]


def test_advisory_proposal_simulate_returns_cached_response_on_same_payload(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_4", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }
    headers = {"Idempotency-Key": "prop-key-4"}

    first = client.post("/advisory/proposals/simulate", json=payload, headers=headers)
    second = client.post("/advisory/proposals/simulate", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_advisory_proposal_simulate_returns_503_when_idempotency_store_write_fails(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_store_error", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    class _FailingSimulationIdempotencyRepository:
        def get_simulation_idempotency(self, *, idempotency_key):
            return None

        def save_simulation_idempotency(self, record):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "src.api.services.advisory_simulation_service.get_proposal_repository",
        lambda: _FailingSimulationIdempotencyRepository(),
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-store-error"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "PROPOSAL_IDEMPOTENCY_STORE_WRITE_FAILED"


def test_advisory_proposal_simulate_unhandled_error_returns_problem_details(monkeypatch):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_5", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    def _raise_unhandled(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _raise_unhandled,
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/advisory/proposals/simulate",
            json=payload,
            headers={"Idempotency-Key": "prop-key-500"},
        )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "Internal Server Error"
    assert body["status"] == 500
    assert body["instance"] == "/advisory/proposals/simulate"


def test_advisory_proposal_simulate_uses_upstream_authorities_when_available(client, monkeypatch):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_upstream", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    def _simulate_with_lotus_core(**kwargs):
        request = kwargs["request"]
        return run_proposal_simulation(
            portfolio=request.portfolio_snapshot,
            market_data=request.market_data_snapshot,
            shelf=request.shelf_entries,
            options=request.options,
            proposed_cash_flows=request.proposed_cash_flows,
            proposed_trades=request.proposed_trades,
            reference_model=request.reference_model,
            request_hash=kwargs["request_hash"],
            idempotency_key=kwargs["idempotency_key"],
            correlation_id=kwargs["correlation_id"],
        )

    def _enrich_with_lotus_risk(**kwargs):
        return kwargs["proposal_result"]

    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )
    monkeypatch.setattr(
        "src.core.advisory.orchestration.enrich_with_lotus_risk",
        _enrich_with_lotus_risk,
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-upstream"},
    )

    assert response.status_code == 200
    authority = response.json()["explanation"]["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_core"
    assert authority["risk_authority"] == "lotus_risk"
    assert authority["degraded"] is False


def test_advisory_proposal_simulate_sets_risk_authority_only_after_valid_risk_response(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_risk_client", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }
    fake_client = _FakeRiskClient(
        _FakeRiskResponse(status_code=200, payload=_risk_response_payload())
    )

    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.lotus_risk.enrichment.httpx.Client",
        lambda timeout: fake_client,
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-risk-client"},
    )

    assert response.status_code == 200
    body = response.json()
    authority = body["explanation"]["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_core"
    assert authority["risk_authority"] == "lotus_risk"
    assert body["explanation"]["risk_lens"]["source_service"] == "lotus-risk"
    assert body["explanation"]["risk_lens"]["risk_proxy"]["hhi_delta"] == 1600.0
    assert (
        body["explanation"]["risk_lens"]["single_position_concentration"]["top_position_current"][
            "security_id"
        ]
        == "EQ_1"
    )
    assert (
        body["explanation"]["risk_lens"]["issuer_concentration"]["top_issuer_current"]["issuer_id"]
        == "PARENT_1"
    )
    assert body["explanation"]["risk_lens"]["issuer_concentration"]["coverage_ratio_current"] == 1.0


def test_advisory_proposal_simulate_marks_risk_authority_unavailable_when_risk_enrichment_fails(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_prop_api_risk_unavailable",
            "base_currency": "USD",
        },
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")

    def _raise_unavailable(**kwargs):
        raise LotusRiskEnrichmentUnavailableError("LOTUS_RISK_ENRICHMENT_UNAVAILABLE")

    monkeypatch.setattr(
        "src.core.advisory.orchestration.enrich_with_lotus_risk",
        _raise_unavailable,
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-risk-unavailable"},
    )

    assert response.status_code == 200
    body = response.json()
    authority = body["explanation"]["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_core"
    assert authority["risk_authority"] == "unavailable"
    assert authority["degraded"] is True
    assert authority["degraded_reasons"] == ["LOTUS_RISK_ENRICHMENT_UNAVAILABLE"]
    assert "risk_lens" not in body["explanation"]


def test_advisory_proposal_simulate_reports_local_fallback_when_explicitly_enabled(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_fallback", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")

    def _simulate_with_lotus_core(**kwargs):
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-fallback"},
    )

    assert response.status_code == 200
    authority = response.json()["explanation"]["authority_resolution"]
    assert authority["simulation_authority"] == "lotus_advise_local_fallback"
    assert authority["risk_authority"] == "unavailable"
    assert authority["degraded"] is True
    assert authority["degraded_reasons"] == [
        "LOTUS_CORE_SIMULATION_UNAVAILABLE",
        "LOTUS_RISK_ENRICHMENT_UNAVAILABLE",
    ]
    assert response.json()["allocation_lens"]["source"] == "LOTUS_ADVISE_LOCAL_FALLBACK"


def test_advisory_proposal_simulate_disallows_local_fallback_in_production_environment(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_prod_guard", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")

    def _simulate_with_lotus_core(**kwargs):
        raise LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-prod-guard"},
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "LOTUS_CORE_SIMULATION_REQUIRED_IN_THIS_ENVIRONMENT"


def test_advisory_proposal_simulate_requires_lotus_core_when_fallback_disabled(client, monkeypatch):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_core_required", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", raising=False)
    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        lambda **kwargs: (_ for _ in ()).throw(
            LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")
        ),
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-core-required"},
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "LOTUS_CORE_SIMULATION_UNAVAILABLE"


def test_advisory_proposal_simulate_returns_503_when_core_execution_unavailable(
    client, monkeypatch
):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_core_down", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        lambda **kwargs: (_ for _ in ()).throw(
            LotusCoreSimulationUnavailableError("LOTUS_CORE_SIMULATION_UNAVAILABLE")
        ),
    )

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-core-down"},
    )

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"].startswith("LOTUS_CORE_SIMULATION_UNAVAILABLE")


def test_advisory_proposal_simulate_preserves_upstream_contract_error_status(client, monkeypatch):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_contract", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    def _simulate_with_lotus_core(**kwargs):
        raise LotusCoreSimulationUnavailableError(
            "Unsupported canonical simulation contract version: "
            "advisory-simulation.v0. Expected advisory-simulation.v1.",
            status_code=412,
        )

    monkeypatch.setattr(
        "src.core.advisory.orchestration.simulate_with_lotus_core",
        _simulate_with_lotus_core,
    )
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-contract-mismatch"},
    )

    assert response.status_code == 412
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "Upstream Canonical Simulation Error"
    assert "Unsupported canonical simulation contract version" in body["detail"]


def test_advisory_proposal_simulate_returns_drift_analysis_when_reference_model_provided(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_prop_api_14c",
            "base_currency": "USD",
            "positions": [{"instrument_id": "EQ_1", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED", "asset_class": "EQUITY"}],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
        "reference_model": {
            "model_id": "mdl_api_14c",
            "as_of": "2026-02-18",
            "base_currency": "USD",
            "asset_class_targets": [
                {"asset_class": "EQUITY", "weight": "0.9"},
                {"asset_class": "CASH", "weight": "0.1"},
            ],
        },
    }

    response = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-14c"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["drift_analysis"]["reference_model"]["model_id"] == "mdl_api_14c"


def test_advisory_proposal_artifact_endpoint_success(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_prop_api_art_1",
            "base_currency": "SGD",
            "positions": [{"instrument_id": "SG_BOND", "quantity": "10"}],
            "cash_balances": [{"currency": "SGD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "SG_BOND", "price": "100", "currency": "SGD"},
                {"instrument_id": "US_EQ", "price": "100", "currency": "USD"},
            ],
            "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
        },
        "shelf_entries": [
            {
                "instrument_id": "SG_BOND",
                "status": "APPROVED",
                "asset_class": "BOND",
                "issuer_id": "ISS_SG_BOND",
                "liquidity_tier": "L1",
            },
            {
                "instrument_id": "US_EQ",
                "status": "APPROVED",
                "asset_class": "EQUITY",
                "issuer_id": "ISS_US_EQ",
                "liquidity_tier": "L1",
            },
        ],
        "options": {
            "enable_proposal_simulation": True,
            "suitability_thresholds": {
                "single_position_max_weight": "1.00",
                "issuer_max_weight": "1.00",
                "max_weight_by_liquidity_tier": {},
                "cash_band_min_weight": "0",
                "cash_band_max_weight": "1",
            },
        },
        "proposed_cash_flows": [{"currency": "SGD", "amount": "100"}],
        "proposed_trades": [{"side": "BUY", "instrument_id": "US_EQ", "quantity": "2"}],
    }

    response = client.post(
        "/advisory/proposals/artifact",
        json=payload,
        headers={"Idempotency-Key": "prop-art-key-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["artifact_id"].startswith("pa_")
    assert body["proposal_run_id"].startswith("pr_")
    assert body["status"] == "READY"
    assert body["summary"]["recommended_next_step"] == "CLIENT_CONSENT"
    assert body["gate_decision"]["gate"] == "CLIENT_CONSENT_REQUIRED"
    assert body["trades_and_funding"]["trade_list"][0]["instrument_id"] == "US_EQ"
    assert body["evidence_bundle"]["hashes"]["artifact_hash"].startswith("sha256:")


def test_advisory_proposal_artifact_supports_stateful_context_resolution(client, monkeypatch):
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )

    response = client.post(
        "/advisory/proposals/artifact",
        json={
            "input_mode": "stateful",
            "stateful_input": {
                "portfolio_id": "pf_prop_api_art_stateful",
                "as_of": "2026-03-25",
            },
        },
        headers={"Idempotency-Key": "prop-art-key-stateful"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_bundle"]["hashes"]["request_hash"].startswith("sha256:")
    assert body["summary"]["title"] == "Proposal for pf_prop_api_art_stateful"
    assert body["evidence_bundle"]["hashes"]["artifact_hash"].startswith("sha256:")


def test_stateful_simulate_and_artifact_share_warm_lotus_core_context(client, monkeypatch):
    base_url = "http://host.docker.internal:8201"
    monkeypatch.setenv("LOTUS_CORE_QUERY_BASE_URL", base_url)
    query_client = CountingLotusCoreQueryClient(
        build_basic_stateful_query_responses(
            base_url=base_url,
            portfolio_id="pf_stateful_artifact_cache",
            as_of="2026-03-25",
        )
    )
    monkeypatch.setattr(
        "src.integrations.lotus_core.stateful_context.httpx.Client",
        lambda timeout: query_client,
    )
    monkeypatch.setattr(
        "src.core.advisory.orchestration.enrich_with_lotus_risk",
        lambda **kwargs: kwargs["proposal_result"],
    )
    payload = {
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_stateful_artifact_cache",
            "as_of": "2026-03-25",
        },
    }

    simulated = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "stateful-artifact-cache-simulate"},
    )
    artifact = client.post(
        "/advisory/proposals/artifact",
        json=payload,
        headers={"Idempotency-Key": "stateful-artifact-cache-artifact"},
    )

    assert simulated.status_code == 200
    assert artifact.status_code == 200
    assert artifact.json()["summary"]["title"] == "Proposal for pf_stateful_artifact_cache"
    assert query_client.request_count == 3
    fetch_stats = get_stateful_context_fetch_stats_for_tests()
    assert_core_context_fetch_counts(fetch_stats, portfolio=1, positions=1, cash=1)


def test_advisory_proposal_artifact_reuses_idempotent_simulation_response(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_art_2", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }
    headers = {"Idempotency-Key": "prop-art-key-2"}

    first = client.post("/advisory/proposals/artifact", json=payload, headers=headers)
    second = client.post("/advisory/proposals/artifact", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    assert first_body["proposal_run_id"] == second_body["proposal_run_id"]
    assert (
        first_body["evidence_bundle"]["hashes"]["artifact_hash"]
        == second_body["evidence_bundle"]["hashes"]["artifact_hash"]
    )


def test_advisory_proposal_artifact_idempotency_conflict_returns_409(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_art_3", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }
    headers = {"Idempotency-Key": "prop-art-key-3"}

    first = client.post("/advisory/proposals/artifact", json=payload, headers=headers)
    assert first.status_code == 200

    payload["proposed_cash_flows"] = [{"currency": "USD", "amount": "1"}]
    second = client.post("/advisory/proposals/artifact", json=payload, headers=headers)
    assert second.status_code == 409
    assert "IDEMPOTENCY_KEY_CONFLICT" in second.json()["detail"]


def test_advisory_proposal_simulate_allows_different_idempotency_keys(client):
    payload = {
        "portfolio_snapshot": {"portfolio_id": "pf_prop_api_cache", "base_currency": "USD"},
        "market_data_snapshot": {"prices": [], "fx_rates": []},
        "shelf_entries": [],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [],
    }

    first = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-cache-1"},
    )
    second = client.post(
        "/advisory/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-cache-2"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["proposal_run_id"] == second.json()["proposal_run_id"]
