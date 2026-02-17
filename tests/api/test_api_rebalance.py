"""
FILE: tests/api/test_api_rebalance.py
"""

import asyncio
import inspect
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, get_db_session


# Mock DB Dependency to avoid AsyncPG errors in unit tests
async def override_get_db_session():
    yield None  # We don't need a real DB for these tests


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


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


def test_simulate_endpoint_success(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["rebalance_run_id"].startswith("rr_")
    assert "before" in data
    assert "after_simulated" in data
    assert "rule_results" in data
    assert "diagnostics" in data


def test_simulate_missing_idempotency_key_422(client):
    """Verifies that Idempotency-Key is mandatory."""
    payload = get_valid_payload()
    # No headers provided
    response = client.post("/rebalance/simulate", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    # Verify the error is about the missing header
    assert any(e["type"] == "missing" and "Idempotency-Key" in e["loc"] for e in errors)


def test_simulate_payload_validation_error_422(client):
    """Verifies that invalid payloads still return 422."""
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]  # Invalid payload
    headers = {"Idempotency-Key": "test-key-val"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_rfc7807_domain_error_mapping(client):
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
    """Verify DB dependency yields expected stub session value."""
    gen = get_db_session()
    assert inspect.isasyncgen(gen)

    async def consume():
        first = await gen.__anext__()
        assert first is None
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

    asyncio.run(consume())


def test_simulate_blocked_logs_warning(client):
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
