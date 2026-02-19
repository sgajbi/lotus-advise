import pytest
from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app, get_db_session


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    yield
    app.dependency_overrides = original_overrides
    PROPOSAL_IDEMPOTENCY_CACHE.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_advisory_proposal_simulate_endpoint_success(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_prop_api_1",
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

    response = client.post(
        "/rebalance/proposals/simulate",
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
        "/rebalance/proposals/simulate",
        json=payload,
        headers={"Idempotency-Key": "prop-key-2"},
    )
    assert response.status_code == 422
    assert "PROPOSAL_SIMULATION_DISABLED" in response.json()["detail"]


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

    first = client.post("/rebalance/proposals/simulate", json=payload, headers=headers)
    assert first.status_code == 200

    payload["proposed_cash_flows"] = [{"currency": "USD", "amount": "1"}]
    second = client.post("/rebalance/proposals/simulate", json=payload, headers=headers)
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

    first = client.post("/rebalance/proposals/simulate", json=payload, headers=headers)
    second = client.post("/rebalance/proposals/simulate", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


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

    monkeypatch.setattr("src.api.main.run_proposal_simulation", _raise_unhandled)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/rebalance/proposals/simulate",
            json=payload,
            headers={"Idempotency-Key": "prop-key-500"},
        )

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "Internal Server Error"
    assert body["status"] == 500
    assert body["instance"] == "/rebalance/proposals/simulate"


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
        "/rebalance/proposals/simulate",
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
        "/rebalance/proposals/artifact",
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

    first = client.post("/rebalance/proposals/artifact", json=payload, headers=headers)
    second = client.post("/rebalance/proposals/artifact", json=payload, headers=headers)

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

    first = client.post("/rebalance/proposals/artifact", json=payload, headers=headers)
    assert first.status_code == 200

    payload["proposed_cash_flows"] = [{"currency": "USD", "amount": "1"}]
    second = client.post("/rebalance/proposals/artifact", json=payload, headers=headers)
    assert second.status_code == 409
    assert "IDEMPOTENCY_KEY_CONFLICT" in second.json()["detail"]
