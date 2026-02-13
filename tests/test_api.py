from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_check():
    """Acceptance: The API must expose a health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "version": "MVP-1"}


def test_simulate_endpoint_success():
    """Integration: The API must successfully route a valid simulation request."""
    payload = {
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
    headers = {"Idempotency-Key": "test-key-123"}

    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert len(data["intents"]) == 1
    assert data["intents"][0]["action"] == "BUY"


def test_simulate_missing_idempotency_key():
    """Acceptance: The API must reject requests missing the Idempotency-Key header."""
    response = client.post("/rebalance/simulate", json={})
    # FastAPI automatically returns 422 Unprocessable Entity for missing required headers/body
    assert response.status_code == 422
    assert "Idempotency-Key" in response.text


def test_simulate_rfc7807_error_handling():
    """Integration: Domain exceptions must be caught and formatted as RFC 7807 problem details."""
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_001",
            "base_currency": "SGD",
            "cash_balances": [{"currency": "SGD", "amount": "100000.00"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "US_EQ_ETF", "price": "100.00", "currency": "USD"}],
            "fx_rates": [],  # Intentionally missing USD/SGD rate to trigger a ValueError
        },
        "model_portfolio": {"targets": [{"instrument_id": "US_EQ_ETF", "weight": "1.00"}]},
        "shelf_entries": [{"instrument_id": "US_EQ_ETF", "status": "APPROVED"}],
        "options": {"suppress_dust_trades": True, "fx_buffer_pct": "0.01"},
    }
    headers = {"Idempotency-Key": "test-key-500", "X-Correlation-Id": "corr-500"}

    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["type"] == "https://api.dpm.com/errors/internal-server-error"
    assert detail["correlation_id"] == "corr-500"
    assert "Missing FX rate" in detail["detail"]
