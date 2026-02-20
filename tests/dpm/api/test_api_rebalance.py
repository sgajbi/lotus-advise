"""
FILE: tests/api/test_api_rebalance.py
"""

import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import DPM_IDEMPOTENCY_CACHE, app, get_db_session
from src.api.routers.dpm_runs import (
    get_dpm_run_support_service,
    reset_dpm_run_support_service_for_tests,
)
from tests.shared.factories import valid_api_payload


async def override_get_db_session():
    yield None


@pytest.fixture(autouse=True)
def override_db_dependency():
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db_session] = override_get_db_session
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    yield
    DPM_IDEMPOTENCY_CACHE.clear()
    reset_dpm_run_support_service_for_tests()
    app.dependency_overrides = original_overrides


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def get_valid_payload():
    return valid_api_payload()


def test_simulate_endpoint_success(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-1", "X-Correlation-Id": "corr-1"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["rebalance_run_id"].startswith("rr_")
    assert data["correlation_id"] == "corr-1"
    assert "before" in data
    assert "after_simulated" in data
    assert "rule_results" in data
    assert "diagnostics" in data
    assert data["gate_decision"]["gate"] in {
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "CLIENT_CONSENT_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    }


def test_simulate_missing_idempotency_key_422(client):
    """Verifies that Idempotency-Key is mandatory."""
    payload = get_valid_payload()
    response = client.post("/rebalance/simulate", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["type"] == "missing" and "Idempotency-Key" in e["loc"] for e in errors)


def test_simulate_payload_validation_error_422(client):
    """Verifies that invalid payloads still return 422."""
    payload = get_valid_payload()
    del payload["portfolio_snapshot"]
    headers = {"Idempotency-Key": "test-key-val"}
    response = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_simulate_idempotency_replay_returns_same_payload(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-replay", "X-Correlation-Id": "corr-idem-replay"}

    first = client.post("/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_simulate_idempotency_conflict_returns_409(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-conflict"}

    first = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert first.status_code == 200

    changed = get_valid_payload()
    changed["options"]["max_turnover_pct"] = "0.05"
    conflict = client.post("/rebalance/simulate", json=changed, headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT: request hash mismatch"


def test_simulate_idempotency_replay_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("DPM_IDEMPOTENCY_REPLAY_ENABLED", "false")
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-idem-disabled"}

    first = client.post("/rebalance/simulate", json=payload, headers=headers)
    second = client.post("/rebalance/simulate", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["rebalance_run_id"] != second.json()["rebalance_run_id"]


def test_dpm_support_apis_lookup_by_run_correlation_and_idempotency(client):
    payload = get_valid_payload()
    headers = {"Idempotency-Key": "test-key-support-1", "X-Correlation-Id": "corr-support-1"}
    simulate = client.post("/rebalance/simulate", json=payload, headers=headers)
    assert simulate.status_code == 200
    body = simulate.json()

    by_run = client.get(f"/rebalance/runs/{body['rebalance_run_id']}")
    assert by_run.status_code == 200
    run_body = by_run.json()
    assert run_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert run_body["correlation_id"] == "corr-support-1"
    assert run_body["idempotency_key"] == "test-key-support-1"
    assert run_body["request_hash"].startswith("sha256:")
    assert run_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]

    by_correlation = client.get("/rebalance/runs/by-correlation/corr-support-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["rebalance_run_id"] == body["rebalance_run_id"]

    by_idempotency = client.get("/rebalance/runs/idempotency/test-key-support-1")
    assert by_idempotency.status_code == 200
    idem_body = by_idempotency.json()
    assert idem_body["idempotency_key"] == "test-key-support-1"
    assert idem_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert idem_body["request_hash"].startswith("sha256:")

    artifact = client.get(f"/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact.status_code == 200
    artifact_body = artifact.json()
    assert artifact_body["artifact_id"].startswith("dra_")
    assert artifact_body["artifact_version"] == "1.0"
    assert artifact_body["rebalance_run_id"] == body["rebalance_run_id"]
    assert artifact_body["correlation_id"] == "corr-support-1"
    assert artifact_body["idempotency_key"] == "test-key-support-1"
    assert artifact_body["portfolio_id"] == payload["portfolio_snapshot"]["portfolio_id"]
    assert artifact_body["status"] == body["status"]
    assert artifact_body["request_snapshot"]["request_hash"].startswith("sha256:")
    assert (
        artifact_body["request_snapshot"]["portfolio_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert artifact_body["evidence"]["hashes"]["request_hash"].startswith("sha256:")
    assert artifact_body["evidence"]["hashes"]["artifact_hash"].startswith("sha256:")
    assert artifact_body["result"]["rebalance_run_id"] == body["rebalance_run_id"]

    artifact_again = client.get(f"/rebalance/runs/{body['rebalance_run_id']}/artifact")
    assert artifact_again.status_code == 200
    assert (
        artifact_again.json()["evidence"]["hashes"]["artifact_hash"]
        == artifact_body["evidence"]["hashes"]["artifact_hash"]
    )


def test_dpm_support_apis_not_found_and_disabled(client, monkeypatch):
    missing_run = client.get("/rebalance/runs/rr_missing")
    assert missing_run.status_code == 404
    assert missing_run.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_correlation = client.get("/rebalance/runs/by-correlation/corr-missing")
    assert missing_correlation.status_code == 404
    assert missing_correlation.json()["detail"] == "DPM_RUN_NOT_FOUND"

    missing_idem = client.get("/rebalance/runs/idempotency/idem-missing")
    assert missing_idem.status_code == 404
    assert missing_idem.json()["detail"] == "DPM_IDEMPOTENCY_KEY_NOT_FOUND"

    missing_artifact = client.get("/rebalance/runs/rr_missing/artifact")
    assert missing_artifact.status_code == 404
    assert missing_artifact.json()["detail"] == "DPM_RUN_NOT_FOUND"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "false")
    disabled = client.get("/rebalance/runs/rr_missing")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_SUPPORT_APIS_DISABLED"

    monkeypatch.setenv("DPM_SUPPORT_APIS_ENABLED", "true")
    monkeypatch.setenv("DPM_ARTIFACTS_ENABLED", "false")
    artifact_disabled = client.get("/rebalance/runs/rr_missing/artifact")
    assert artifact_disabled.status_code == 404
    assert artifact_disabled.json()["detail"] == "DPM_ARTIFACTS_DISABLED"


def test_dpm_async_operation_lookup_not_found_and_disabled(client, monkeypatch):
    missing = client.get("/rebalance/operations/dop_missing")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    missing_by_corr = client.get("/rebalance/operations/by-correlation/corr-missing")
    assert missing_by_corr.status_code == 404
    assert missing_by_corr.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")
    disabled = client.get("/rebalance/operations/dop_missing")
    assert disabled.status_code == 404
    assert disabled.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_dpm_async_operation_lookup_by_id_and_correlation(client):
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(correlation_id="corr-dpm-async-support-1")

    by_operation = client.get(f"/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["operation_id"] == accepted.operation_id
    assert by_operation_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert by_operation_body["status"] == "PENDING"
    assert by_operation_body["correlation_id"] == "corr-dpm-async-support-1"
    assert by_operation_body["result"] is None
    assert by_operation_body["error"] is None

    by_correlation = client.get("/rebalance/operations/by-correlation/corr-dpm-async-support-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == accepted.operation_id


def test_dpm_async_operation_ttl_expiry_by_id_and_correlation(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_TTL_SECONDS", "1")
    reset_dpm_run_support_service_for_tests()
    service = get_dpm_run_support_service()
    accepted = service.submit_analyze_async(
        correlation_id="corr-dpm-async-ttl-expired",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=10),
    )

    by_operation = client.get(f"/rebalance/operations/{accepted.operation_id}")
    assert by_operation.status_code == 404
    assert by_operation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"

    by_correlation = client.get("/rebalance/operations/by-correlation/corr-dpm-async-ttl-expired")
    assert by_correlation.status_code == 404
    assert by_correlation.json()["detail"] == "DPM_ASYNC_OPERATION_NOT_FOUND"


def test_simulate_defaults_correlation_id_to_c_none_when_header_missing(client):
    payload = get_valid_payload()
    response = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-corr-none"},
    )
    assert response.status_code == 200
    assert response.json()["correlation_id"] == "c_none"


def test_simulate_rfc7807_domain_error_mapping(client):
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
    payload["market_data_snapshot"]["prices"] = []

    headers = {"Idempotency-Key": "test-key-block"}
    with patch("src.api.main.logger") as mock_logger:
        response = client.post("/rebalance/simulate", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "BLOCKED"

        mock_logger.warning.assert_called()
        args, _ = mock_logger.warning.call_args
        assert "Run blocked" in args[0]


def test_simulate_missing_price_can_continue_when_non_blocking(client):
    payload = get_valid_payload()
    payload["market_data_snapshot"]["prices"] = []
    payload["options"]["block_on_missing_prices"] = False

    response = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-missing-price-nonblock"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"READY", "PENDING_REVIEW"}
    assert "EQ_1" in body["diagnostics"]["data_quality"]["price_missing"]


def test_simulate_rejects_invalid_group_constraint_key(client):
    payload = get_valid_payload()
    payload["options"]["group_constraints"] = {"sectorTECH": {"max_weight": "0.2"}}

    response = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-invalid-group-key"},
    )

    assert response.status_code == 422


def test_analyze_endpoint_success(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["snapshot_id"] = "ps_13"
    payload["market_data_snapshot"]["snapshot_id"] = "md_13"
    payload["scenarios"] = {
        "baseline": {"options": {}},
        "position_cap": {"options": {"single_position_max_weight": "0.5"}},
    }

    response = client.post(
        "/rebalance/analyze",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["batch_run_id"].startswith("batch_")
    assert "run_at_utc" in body
    assert body["base_snapshot_ids"]["portfolio_snapshot_id"] == "ps_13"
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md_13"
    assert set(body["results"].keys()) == {"baseline", "position_cap"}
    assert set(body["comparison_metrics"].keys()) == {"baseline", "position_cap"}
    assert body["failed_scenarios"] == {}
    assert body["warnings"] == []

    for scenario_result in body["results"].values():
        assert scenario_result["lineage"]["request_hash"].startswith(body["batch_run_id"])
    assert body["results"]["baseline"]["correlation_id"] == "corr-batch-1:baseline"
    assert body["results"]["position_cap"]["correlation_id"] == "corr-batch-1:position_cap"
    for metrics in body["comparison_metrics"].values():
        assert metrics["status"] in {"READY", "PENDING_REVIEW", "BLOCKED"}
        assert isinstance(metrics["security_intent_count"], int)
        assert (
            metrics["gross_turnover_notional_base"]["currency"]
            == payload["portfolio_snapshot"]["base_currency"]
        )


def test_analyze_async_accept_and_lookup_succeeded(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-1"},
    )
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["operation_type"] == "ANALYZE_SCENARIOS"
    assert accepted_body["status"] == "PENDING"
    assert accepted_body["correlation_id"] == "corr-batch-async-1"
    assert accepted.headers["X-Correlation-Id"] == "corr-batch-async-1"
    operation_id = accepted_body["operation_id"]

    by_operation = client.get(f"/rebalance/operations/{operation_id}")
    assert by_operation.status_code == 200
    by_operation_body = by_operation.json()
    assert by_operation_body["status"] == "SUCCEEDED"
    assert by_operation_body["correlation_id"] == "corr-batch-async-1"
    assert by_operation_body["result"]["batch_run_id"].startswith("batch_")
    assert set(by_operation_body["result"]["results"].keys()) == {"baseline"}
    assert by_operation_body["error"] is None

    by_correlation = client.get("/rebalance/operations/by-correlation/corr-batch-async-1")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "SUCCEEDED"


def test_analyze_async_generates_and_echoes_correlation_header_when_missing(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post("/rebalance/analyze/async", json=payload)
    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["correlation_id"].startswith("corr_")
    assert accepted.headers["X-Correlation-Id"] == accepted_body["correlation_id"]


def test_analyze_async_failure_is_captured_in_operation_status(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    with patch("src.api.main._execute_batch_analysis", side_effect=RuntimeError("boom")):
        accepted = client.post(
            "/rebalance/analyze/async",
            json=payload,
            headers={"X-Correlation-Id": "corr-batch-async-failure"},
        )

    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    operation = client.get(f"/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "FAILED"
    assert operation_body["result"] is None
    assert operation_body["error"]["code"] == "RuntimeError"
    assert operation_body["error"]["message"] == "boom"


def test_analyze_async_disabled_returns_404(client, monkeypatch):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}
    monkeypatch.setenv("DPM_ASYNC_OPERATIONS_ENABLED", "false")

    response = client.post("/rebalance/analyze/async", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "DPM_ASYNC_OPERATIONS_DISABLED"


def test_analyze_async_accept_only_mode_keeps_operation_pending(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "ACCEPT_ONLY")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-accept-only"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    operation_body = operation.json()
    assert operation_body["status"] == "PENDING"
    assert operation_body["started_at"] is None
    assert operation_body["finished_at"] is None
    assert operation_body["result"] is None
    assert operation_body["error"] is None

    by_correlation = client.get("/rebalance/operations/by-correlation/corr-batch-async-accept-only")
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_correlation.json()["status"] == "PENDING"


def test_analyze_async_invalid_execution_mode_falls_back_to_inline(client, monkeypatch):
    monkeypatch.setenv("DPM_ASYNC_EXECUTION_MODE", "INVALID_MODE")
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    accepted = client.post(
        "/rebalance/analyze/async",
        json=payload,
        headers={"X-Correlation-Id": "corr-batch-async-inline-fallback"},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]

    operation = client.get(f"/rebalance/operations/{operation_id}")
    assert operation.status_code == 200
    assert operation.json()["status"] == "SUCCEEDED"


def test_dpm_artifact_openapi_schema_has_descriptions_and_examples(client):
    openapi = client.get("/openapi.json").json()
    schema = openapi["components"]["schemas"]["DpmRunArtifactResponse"]
    for property_name in [
        "artifact_id",
        "artifact_version",
        "rebalance_run_id",
        "correlation_id",
        "portfolio_id",
        "status",
        "request_snapshot",
        "before_summary",
        "after_summary",
        "order_intents",
        "rule_outcomes",
        "diagnostics",
        "result",
        "evidence",
    ]:
        prop = schema["properties"][property_name]
        assert prop.get("description")
        assert prop.get("examples") or prop.get("$ref")


def test_openapi_title_and_tag_grouping(client):
    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["title"] == "Private Banking Rebalance API"

    tags = {tag["name"] for tag in openapi.get("tags", [])}
    assert "DPM Simulation" in tags
    assert "DPM What-If Analysis" in tags
    assert "DPM Run Supportability" in tags
    assert "Advisory Simulation" in tags
    assert "Advisory Proposal Lifecycle" in tags

    assert openapi["paths"]["/rebalance/simulate"]["post"]["tags"] == ["DPM Simulation"]
    assert openapi["paths"]["/rebalance/analyze"]["post"]["tags"] == ["DPM What-If Analysis"]
    assert openapi["paths"]["/rebalance/analyze/async"]["post"]["tags"] == ["DPM What-If Analysis"]
    assert openapi["paths"]["/rebalance/proposals/simulate"]["post"]["tags"] == [
        "Advisory Simulation"
    ]


def test_openapi_async_analyze_documents_correlation_header(client):
    openapi = client.get("/openapi.json").json()
    analyze_async = openapi["paths"]["/rebalance/analyze/async"]["post"]

    request_header = next(
        parameter
        for parameter in analyze_async["parameters"]
        if parameter["name"] == "X-Correlation-Id"
    )
    assert request_header["in"] == "header"
    assert request_header["description"]
    schema = request_header["schema"]
    if "type" in schema:
        assert schema["type"] == "string"
    else:
        assert any(item.get("type") == "string" for item in schema.get("anyOf", []))

    response_headers = analyze_async["responses"]["202"]["headers"]
    assert "X-Correlation-Id" in response_headers
    assert response_headers["X-Correlation-Id"]["description"]
    assert response_headers["X-Correlation-Id"]["schema"]["type"] == "string"


def test_analyze_rejects_invalid_scenario_name(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"Invalid-Name": {"options": {}}}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_partial_failure_invalid_scenario_options(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "valid_case": {"options": {}},
        "invalid_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert "valid_case" in body["results"]
    assert "invalid_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["invalid_case"].startswith("INVALID_OPTIONS:")
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_rejects_too_many_scenarios(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i}": {"options": {}} for i in range(21)}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_fallback_snapshot_ids_when_not_provided(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert (
        body["base_snapshot_ids"]["portfolio_snapshot_id"]
        == payload["portfolio_snapshot"]["portfolio_id"]
    )
    assert body["base_snapshot_ids"]["market_data_snapshot_id"] == "md"


def test_analyze_scenarios_are_processed_in_sorted_name_order(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"z_case": {"options": {}}, "a_case": {"options": {}}}

    from src.core.dpm_engine import run_simulation as real_run
    from src.core.models import (
        EngineOptions,
        MarketDataSnapshot,
        ModelPortfolio,
        PortfolioSnapshot,
        ShelfEntry,
    )

    seed_payload = get_valid_payload()
    real_result = real_run(
        portfolio=PortfolioSnapshot(**seed_payload["portfolio_snapshot"]),
        market_data=MarketDataSnapshot(**seed_payload["market_data_snapshot"]),
        model=ModelPortfolio(**seed_payload["model_portfolio"]),
        shelf=[ShelfEntry(**entry) for entry in seed_payload["shelf_entries"]],
        options=EngineOptions(**seed_payload["options"]),
        request_hash="seed",
    )

    with patch("src.api.main.run_simulation") as mock_run:
        mock_run.return_value = real_result

        response = client.post("/rebalance/analyze", json=payload)
        assert response.status_code == 200
        call_hashes = [c.kwargs["request_hash"] for c in mock_run.call_args_list]
        assert call_hashes[0].endswith(":a_case")
        assert call_hashes[1].endswith(":z_case")


def test_analyze_runtime_error_is_isolated_to_failing_scenario(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"ok_case": {"options": {}}, "boom_case": {"options": {}}}

    from src.api.main import run_simulation as real_run

    def _side_effect(*args, **kwargs):
        if kwargs.get("request_hash", "").endswith(":boom_case"):
            raise RuntimeError("boom")
        return real_run(*args, **kwargs)

    with patch("src.api.main.run_simulation", side_effect=_side_effect):
        response = client.post("/rebalance/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert "ok_case" in body["results"]
    assert "boom_case" in body["failed_scenarios"]
    assert body["failed_scenarios"]["boom_case"] == "SCENARIO_EXECUTION_ERROR: RuntimeError"
    assert "PARTIAL_BATCH_FAILURE" in body["warnings"]


def test_analyze_comparison_metrics_turnover_matches_intents(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["positions"] = [{"instrument_id": "EQ_1", "quantity": "100"}]
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "0"}]
    payload["model_portfolio"]["targets"] = [{"instrument_id": "EQ_1", "weight": "0.0"}]
    payload["shelf_entries"] = [{"instrument_id": "EQ_1", "status": "APPROVED"}]
    payload["scenarios"] = {"de_risk": {"options": {}}}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    metric = body["comparison_metrics"]["de_risk"]
    result = body["results"]["de_risk"]
    expected_turnover = sum(
        Decimal(intent["notional_base"]["amount"])
        for intent in result["intents"]
        if intent["intent_type"] == "SECURITY_TRADE"
    )
    assert Decimal(metric["gross_turnover_notional_base"]["amount"]) == expected_turnover


def test_analyze_accepts_max_scenarios_boundary(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {f"s{i:02d}": {"options": {}} for i in range(20)}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 20
    assert len(body["comparison_metrics"]) == 20
    assert body["failed_scenarios"] == {}


def test_analyze_run_at_utc_is_timezone_aware_iso8601(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {"baseline": {"options": {}}}

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    run_at = datetime.fromisoformat(response.json()["run_at_utc"])
    assert run_at.tzinfo is not None


def test_analyze_results_and_metrics_keys_match_successful_scenarios_only(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["scenarios"] = {
        "ok_case": {"options": {}},
        "bad_case": {"options": {"group_constraints": {"sectorTECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body["results"].keys()) == {"ok_case"}
    assert set(body["comparison_metrics"].keys()) == {"ok_case"}
    assert set(body["failed_scenarios"].keys()) == {"bad_case"}


def test_analyze_mixed_outcomes_ready_pending_review_blocked(client):
    payload = get_valid_payload()
    payload.pop("options")
    payload["shelf_entries"] = [
        {
            "instrument_id": "EQ_1",
            "status": "APPROVED",
            "attributes": {"sector": "TECH"},
        }
    ]
    payload["scenarios"] = {
        "ready_case": {"options": {}},
        "pending_case": {"options": {"single_position_max_weight": "0.5"}},
        "blocked_case": {"options": {"group_constraints": {"sector:TECH": {"max_weight": "0.2"}}}},
    }

    response = client.post("/rebalance/analyze", json=payload)
    assert response.status_code == 200
    metrics = response.json()["comparison_metrics"]
    assert metrics["ready_case"]["status"] == "READY"
    assert metrics["pending_case"]["status"] == "PENDING_REVIEW"
    assert metrics["blocked_case"]["status"] == "BLOCKED"


def test_simulate_turnover_cap_emits_partial_rebalance_warning(client):
    payload = get_valid_payload()
    payload["portfolio_snapshot"]["base_currency"] = "USD"
    payload["portfolio_snapshot"]["cash_balances"] = [{"currency": "USD", "amount": "100000"}]
    payload["market_data_snapshot"]["prices"] = [
        {"instrument_id": "A", "price": "100", "currency": "USD"},
        {"instrument_id": "B", "price": "100", "currency": "USD"},
        {"instrument_id": "C", "price": "100", "currency": "USD"},
    ]
    payload["model_portfolio"]["targets"] = [
        {"instrument_id": "A", "weight": "0.10"},
        {"instrument_id": "B", "weight": "0.10"},
        {"instrument_id": "C", "weight": "0.02"},
    ]
    payload["shelf_entries"] = [
        {"instrument_id": "A", "status": "APPROVED"},
        {"instrument_id": "B", "status": "APPROVED"},
        {"instrument_id": "C", "status": "APPROVED"},
    ]
    payload["options"]["max_turnover_pct"] = "0.15"

    response = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-turnover-cap"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "PARTIAL_REBALANCE_TURNOVER_LIMIT" in body["diagnostics"]["warnings"]
    assert len(body["diagnostics"]["dropped_intents"]) == 1


def test_simulate_settlement_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_settlement_api",
            "base_currency": "USD",
            "positions": [{"instrument_id": "SLOW_FUND", "quantity": "10"}],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [
                {"instrument_id": "SLOW_FUND", "price": "100", "currency": "USD"},
                {"instrument_id": "FAST_STOCK", "price": "100", "currency": "USD"},
            ],
            "fx_rates": [],
        },
        "model_portfolio": {
            "targets": [
                {"instrument_id": "SLOW_FUND", "weight": "0.0"},
                {"instrument_id": "FAST_STOCK", "weight": "1.0"},
            ]
        },
        "shelf_entries": [
            {"instrument_id": "SLOW_FUND", "status": "APPROVED", "settlement_days": 3},
            {"instrument_id": "FAST_STOCK", "status": "APPROVED", "settlement_days": 1},
        ],
        "options": {"enable_settlement_awareness": False},
    }

    disabled = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-off"},
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "READY"

    payload["options"]["enable_settlement_awareness"] = True
    payload["options"]["settlement_horizon_days"] = 3

    enabled = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-settlement-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert body["status"] == "BLOCKED"
    assert "OVERDRAFT_ON_T_PLUS_1" in body["diagnostics"]["warnings"]


def test_simulate_tax_awareness_toggle_is_request_scoped(client):
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_tax_api",
            "base_currency": "USD",
            "positions": [
                {
                    "instrument_id": "ABC",
                    "quantity": "100",
                    "lots": [
                        {
                            "lot_id": "L_LOW",
                            "quantity": "50",
                            "unit_cost": {"amount": "10", "currency": "USD"},
                            "purchase_date": "2024-01-01",
                        },
                        {
                            "lot_id": "L_HIGH",
                            "quantity": "50",
                            "unit_cost": {"amount": "100", "currency": "USD"},
                            "purchase_date": "2024-02-01",
                        },
                    ],
                }
            ],
            "cash_balances": [{"currency": "USD", "amount": "0"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "ABC", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "model_portfolio": {"targets": [{"instrument_id": "ABC", "weight": "0.0"}]},
        "shelf_entries": [{"instrument_id": "ABC", "status": "APPROVED"}],
        "options": {
            "enable_tax_awareness": False,
            "max_realized_capital_gains": "100",
        },
    }

    disabled = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-off"},
    )
    assert disabled.status_code == 200
    assert Decimal(disabled.json()["intents"][0]["quantity"]) == Decimal("100")
    assert disabled.json()["tax_impact"] is None

    payload["options"]["enable_tax_awareness"] = True
    enabled = client.post(
        "/rebalance/simulate",
        json=payload,
        headers={"Idempotency-Key": "test-key-tax-on"},
    )
    assert enabled.status_code == 200
    body = enabled.json()
    assert Decimal(body["intents"][0]["quantity"]) < Decimal("100")
    assert "TAX_BUDGET_LIMIT_REACHED" in body["diagnostics"]["warnings"]
    assert body["tax_impact"]["budget_used"]["amount"] == "100"
