from fastapi.testclient import TestClient

from src.api.main import MOCK_DB_IDEMPOTENCY, MOCK_DB_RUNS, app

client = TestClient(app)


def setup_function():
    """Clear the mock DBs before each test to ensure isolation."""
    MOCK_DB_IDEMPOTENCY.clear()
    MOCK_DB_RUNS.clear()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200


def get_valid_payload():
    return {
        "portfolio_snapshot": {
            "portfolio_id": "pf_001",
            "base_currency": "SGD",
            "cash_balances": [{"currency": "SGD", "amount": "100000.00"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "SG_EQ_ETF", "price": "100.00", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "SG_EQ_ETF", "weight": "1.00"}]},
        "shelf_entries": [
            {
                "instrument_id": "SG_EQ_ETF",
                "status": "APPROVED",
                "min_notional": {"amount": "1000", "currency": "SGD"},
            }
        ],
        "options": {"suppress_dust_trades": True, "fx_buffer_pct": "0.01"},
    }


def test_simulate_endpoint_success_and_idempotency():
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-123", "X-Correlation-Id": "corr-1"}

    # 1. First Call (Cache Miss)
    response_1 = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response_1.status_code == 200
    data_1 = response_1.json()
    assert data_1["status"] == "READY"
    assert data_1["correlation_id"] == "corr-1"
    run_id_1 = data_1["rebalance_run_id"]

    # 2. Second Call (Cache Hit)
    response_2 = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response_2.status_code == 200
    data_2 = response_2.json()
    # It must return the EXACT same run_id without re-processing
    assert data_2["rebalance_run_id"] == run_id_1


def test_simulate_idempotency_conflict():
    headers = {"Idempotency-Key": "test-key-conflict"}

    # 1. Call with Payload A
    payload_a = get_valid_payload()
    client.post("/rebalance/simulate", json=payload_a, headers=headers)

    # 2. Call with Payload B (different options), using the SAME key
    payload_b = get_valid_payload()
    payload_b["options"]["suppress_dust_trades"] = False

    response = client.post("/rebalance/simulate", json=payload_b, headers=headers)

    # Should throw HTTP 409 Conflict
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_CONFLICT"


def test_simulate_rfc7807_domain_error_mapping():
    # Force a domain error by causing an infeasible constraint
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    # Engine throws ValueError, API maps to 422
    assert response.status_code == 422
    detail = response.json()
    assert detail["error_code"] == "CONSTRAINT_INFEASIBLE"
    assert detail["correlation_id"] == "corr-err"
    assert "status" in detail


def test_simulate_rfc7807_generic_domain_error_mapping():
    payload = get_valid_payload()
    # Trigger a "Missing shelf entry" ValueError to hit the generic fallback block
    payload["shelf_entries"] = []

    headers = {"Idempotency-Key": "test-key-generic-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "UNPROCESSABLE_DOMAIN_ERROR"

    """Hits lines 43-46 in api/main.py: Fallback to UNPROCESSABLE_DOMAIN_ERROR."""
    payload = get_valid_payload()
    # Setting an empty string for portfolio_id might pass Pydantic but could
    # theoretically trigger a generic ValueError in a more complex engine.
    # To artificially trigger the exact API fallback block, we will send an
    # un-resolvable FX deficit that throws a generic ValueError("Missing FX rate").
    payload["portfolio_snapshot"]["cash_balances"] = []
    payload["market_data_snapshot"]["prices"] = [
        {"instrument_id": "US_EQ_ETF", "price": "100.00", "currency": "USD"}
    ]
    payload["model_portfolio"] = {"targets": [{"instrument_id": "US_EQ_ETF", "weight": "1.00"}]}
    payload["shelf_entries"] = [{"instrument_id": "US_EQ_ETF", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-generic-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 422
    assert response.json()["error_code"] == "DATA_QUALITY_ERROR"
