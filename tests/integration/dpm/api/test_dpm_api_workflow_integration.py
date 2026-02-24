from fastapi.testclient import TestClient

from src.api.main import DPM_IDEMPOTENCY_CACHE, app, get_db_session
from src.api.routers.dpm_runs import reset_dpm_run_support_service_for_tests
from tests.shared.factories import valid_api_payload


async def _override_get_db_session():
    yield None


_ORIGINAL_OVERRIDES: dict = {}


def setup_function() -> None:
    global _ORIGINAL_OVERRIDES
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = _override_get_db_session
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    _ORIGINAL_OVERRIDES = original_overrides


def teardown_function() -> None:
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = _ORIGINAL_OVERRIDES


def test_simulate_then_supportability_endpoints_roundtrip() -> None:
    payload = valid_api_payload()
    headers = {"Idempotency-Key": "integration-dpm-1", "X-Correlation-Id": "corr-integration-dpm-1"}

    with TestClient(app) as client:
        simulate = client.post("/rebalance/simulate", json=payload, headers=headers)
        assert simulate.status_code == 200
        run = simulate.json()

        by_run = client.get(f"/rebalance/runs/{run['rebalance_run_id']}")
        by_correlation = client.get("/rebalance/runs/by-correlation/corr-integration-dpm-1")
        by_idempotency = client.get("/rebalance/runs/idempotency/integration-dpm-1")
        artifact = client.get(f"/rebalance/runs/{run['rebalance_run_id']}/artifact")
        summary = client.get("/rebalance/supportability/summary")

    assert by_run.status_code == 200
    assert by_correlation.status_code == 200
    assert by_idempotency.status_code == 200
    assert artifact.status_code == 200
    assert summary.status_code == 200

    assert by_run.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert by_correlation.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert by_idempotency.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert artifact.json()["rebalance_run_id"] == run["rebalance_run_id"]
    assert summary.json()["run_count"] >= 1


def test_run_list_and_operation_lookup_integration_flow() -> None:
    payload = valid_api_payload()
    payload.pop("options", None)
    payload["scenarios"] = {"baseline": {"options": {}}}
    headers = {
        "Idempotency-Key": "integration-dpm-async-1",
        "X-Correlation-Id": "corr-integration-dpm-async-1",
    }

    with TestClient(app) as client:
        accepted = client.post("/rebalance/analyze/async", json=payload, headers=headers)
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        operation = client.get(f"/rebalance/operations/{operation_id}")
        by_correlation = client.get(
            "/rebalance/operations/by-correlation/corr-integration-dpm-async-1"
        )
        listed = client.get("/rebalance/operations?limit=10")

    assert operation.status_code == 200
    assert by_correlation.status_code == 200
    assert listed.status_code == 200
    assert operation.json()["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id
    assert len(listed.json()["items"]) >= 1
