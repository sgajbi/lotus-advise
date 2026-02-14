from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def get_valid_payload():
    return {
        "portfolio_snapshot": {
            "portfolio_id": "pf_001",
            "base_currency": "SGD",
            "positions": [],
            "cash_balances": [
                {"currency": "SGD", "amount": "10000.00"},
                {"currency": "USD", "amount": "5000.00"},
            ],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "EQ_1", "price": "100.00", "currency": "SGD"},
                {"instrument_id": "EQ_2", "price": "50.00", "currency": "USD"},
            ],
            "fx_rates": [{"pair": "USD/SGD", "rate": "1.35"}],
        },
        "model_portfolio": {
            "targets": [
                {"instrument_id": "EQ_1", "weight": "0.6"},
                {"instrument_id": "EQ_2", "weight": "0.4"},
            ]
        },
        "shelf_entries": [
            {"instrument_id": "EQ_1", "status": "APPROVED"},
            {"instrument_id": "EQ_2", "status": "APPROVED"},
        ],
        "options": {
            "allow_restricted": False,
            "suppress_dust_trades": True,
            "dust_trade_threshold": {"amount": "1.0", "currency": "SGD"},
            "fx_buffer_pct": "0.01",
        },
    }


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_simulate_valid_payload():
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["READY", "PENDING_REVIEW"]
    assert data["correlation_id"] == "corr-1"


def test_simulate_idempotency_hit():
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-2"}
    # First call
    resp1 = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert resp1.status_code == 200
    run_id_1 = resp1.json()["rebalance_run_id"]

    # Second call (same key)
    resp2 = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["rebalance_run_id"] == run_id_1


def test_simulate_idempotency_conflict():
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-3"}
    client.post("/rebalance/simulate", json=payload, headers=headers)

    # Conflict call (same key, different payload)
    payload["options"]["allow_restricted"] = True
    resp2 = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert resp2.status_code == 409


def test_simulate_rfc7807_domain_error_mapping():
    # Force a domain error by causing an infeasible constraint
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"
    # Logic: Target 0.6 > 0.5. Engine will cap and try to redistribute.
    # If redistribution fails or is blocked, status becomes BLOCKED.
    # For this test, we just want to ensure we get a 200 OK with BLOCKED status
    # if it fails, OR a 200 OK with READY if it succeeds.
    # To force a BLOCK, let's make it infeasible:
    # Set targets to just one asset at 1.0, but max weight 0.5.
    # Excess 0.5 has nowhere to go. -> BLOCKED.

    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    # RFC-0003: Domain errors return 200 OK with status="BLOCKED"
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"


def test_simulate_rfc7807_generic_domain_error_mapping():
    payload = get_valid_payload()
    # Trigger a "Missing shelf entry" which is now a data quality BLOCK
    payload["shelf_entries"] = []

    headers = {"Idempotency-Key": "test-key-generic-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    # RFC-0003: Missing shelf data returns 200 OK with status="BLOCKED"
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "BLOCKED"
    assert "shelf_missing" in data["diagnostics"]["data_quality"]
