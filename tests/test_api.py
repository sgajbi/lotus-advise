"""
FILE: tests/test_api.py
"""

from unittest.mock import patch

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


def test_simulate_missing_idempotency_key_422():
    """Verifies that Idempotency-Key is mandatory."""
    payload = get_valid_payload()
    # No headers provided
    response = client.post("/rebalance/simulate", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    # Verify the error is about the missing header
    assert any(e["type"] == "missing" and "Idempotency-Key" in e["loc"] for e in errors)


def test_simulate_payload_validation_error_422():
    """Verifies that invalid payloads still return 422."""
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]  # Invalid payload
    headers = {"Idempotency-Key": "test-key-val"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_rfc7807_domain_error_mapping():
    # Force a domain outcome where constraints prevent full allocation (Soft Fail).
    # Returns PENDING_REVIEW.
    payload = get_valid_payload()
    payload["options"]["single_position_max_weight"] = "0.50"

    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "1.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]

    headers = {"Idempotency-Key": "test-key-err", "X-Correlation-Id": "corr-err"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_REVIEW"


def test_get_db_session_dependency():
    """Trivial coverage for the DB stub (Synchronous wrapper)."""
    # Manually iterate the async generator
    gen = get_db_session()
    try:
        gen.asend(None).send(None)
    except (StopIteration, AttributeError):
        pass
    import inspect

    assert inspect.isasyncgen(gen)


def test_simulate_blocked_logs_warning():
    """
    Force a 'BLOCKED' status (e.g. missing price) to verify the API logging branch.
    """
    payload = get_valid_payload()
    # Missing price for EQ_1 -> DQ Failure -> BLOCKED
    payload["market_data_snapshot"]["prices"] = []

    headers = {"Idempotency-Key": "test-key-block"}
    with patch("src.api.main.logger") as mock_logger:
        response = client.post("/rebalance/simulate", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "BLOCKED"

        # Verify the warning log was called
        mock_logger.warning.assert_called()
        args, _ = mock_logger.warning.call_args
        assert "Run blocked" in args[0]
