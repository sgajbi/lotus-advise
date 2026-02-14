"""
FILE: tests/test_api.py
"""

from fastapi.testclient import TestClient

from src.api.main import app, get_db_session

client = TestClient(app)


# Mock DB Dependency to avoid AsyncPG errors in unit tests
async def override_get_db_session():
    yield None  # We don't need a real DB for these tests


app.dependency_overrides[get_db_session] = override_get_db_session


def get_valid_payload():
    return {
        "portfolio_snapshot": {
            "portfolio_id": "pf_1",
            "base_currency": "SGD",
            "positions": [],
            "cash_balances": [{"currency": "SGD", "amount": "10000.00"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100.00", "currency": "SGD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "EQ_1", "weight": "1.0"}]},
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {},
    }


def test_simulate_endpoint_success():
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["rebalance_run_id"].startswith("rr_")


def test_simulate_validation_error_422():
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]  # Invalid payload
    response = client.post("/rebalance/simulate", json=payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_rfc7807_domain_error_mapping():
    # Force a domain outcome where constraints prevent full allocation.
    # Previously this returned BLOCKED, now it returns PENDING_REVIEW (Best Effort).
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"

    # Target 1.0 > Max 0.5. Engine will cap at 0.5 and leave 0.5 as Cash.
    # Result: PENDING_REVIEW.

    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_REVIEW"
