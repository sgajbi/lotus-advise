import pytest
from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests


def _base_create_payload(portfolio_id: str = "pf_integration_proposal_1") -> dict:
    return {
        "created_by": "advisor_integration",
        "metadata": {
            "title": "Integration proposal",
            "advisor_notes": "integration coverage",
            "jurisdiction": "SG",
            "mandate_id": "mandate_integration",
        },
        "simulate_request": {
            "portfolio_snapshot": {
                "portfolio_id": portfolio_id,
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_OLD", "quantity": "10"}],
                "cash_balances": [{"currency": "USD", "amount": "1000"}],
            },
            "market_data_snapshot": {
                "prices": [
                    {"instrument_id": "EQ_OLD", "price": "100", "currency": "USD"},
                    {"instrument_id": "EQ_NEW", "price": "50", "currency": "USD"},
                ],
                "fx_rates": [],
            },
            "shelf_entries": [
                {"instrument_id": "EQ_OLD", "status": "APPROVED"},
                {"instrument_id": "EQ_NEW", "status": "APPROVED"},
            ],
            "options": {"enable_proposal_simulation": True},
            "proposed_cash_flows": [{"currency": "USD", "amount": "100"}],
            "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "2"}],
        },
    }


def setup_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def teardown_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def test_proposal_create_list_get_and_version_roundtrip() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload(),
            headers={"Idempotency-Key": "integration-proposal-create-1"},
        )
        assert created.status_code == 200
        created_body = created.json()
        proposal_id = created_body["proposal"]["proposal_id"]

        listed = client.get(
            "/rebalance/proposals",
            params={"portfolio_id": "pf_integration_proposal_1"},
        )
        detail = client.get(f"/rebalance/proposals/{proposal_id}")
        version = client.get(f"/rebalance/proposals/{proposal_id}/versions/1")
        workflow_events = client.get(f"/rebalance/proposals/{proposal_id}/workflow-events")

    assert listed.status_code == 200
    assert detail.status_code == 200
    assert version.status_code == 200
    assert workflow_events.status_code == 200
    assert listed.json()["items"][0]["proposal_id"] == proposal_id
    assert detail.json()["proposal"]["proposal_id"] == proposal_id
    assert version.json()["version_no"] == 1
    assert workflow_events.json()["events"][0]["event_type"] == "CREATED"


def test_proposal_submit_and_support_endpoints() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload("pf_integration_proposal_2"),
            headers={"Idempotency-Key": "integration-proposal-submit-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        submit = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {"comment": "integration submit"},
            },
        )
        approvals = client.get(f"/rebalance/proposals/{proposal_id}/approvals")
        lineage = client.get(f"/rebalance/proposals/{proposal_id}/lineage")

    assert submit.status_code == 200
    assert approvals.status_code == 200
    assert lineage.status_code == 200
    assert submit.json()["current_state"] == "RISK_REVIEW"


def test_proposal_idempotency_lookup_and_support_config() -> None:
    idempotency_key = "integration-proposal-idem-lookup-1"
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload("pf_integration_proposal_3"),
            headers={"Idempotency-Key": idempotency_key},
        )
        assert created.status_code == 200

        lookup = client.get(f"/rebalance/proposals/idempotency/{idempotency_key}")
        support_config = client.get("/rebalance/proposals/supportability/config")

    assert lookup.status_code == 200
    assert lookup.json()["idempotency_key"] == idempotency_key
    assert support_config.status_code == 200
    assert "backend_ready" in support_config.json()


def test_proposal_support_endpoints_disabled_by_feature_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload("pf_integration_proposal_4"),
            headers={"Idempotency-Key": "integration-proposal-support-disabled-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        monkeypatch.setenv("PROPOSAL_SUPPORT_APIS_ENABLED", "false")
        approvals = client.get(f"/rebalance/proposals/{proposal_id}/approvals")

    assert approvals.status_code == 404
    assert approvals.json()["detail"] == "PROPOSAL_SUPPORT_APIS_DISABLED"


def test_proposal_lifecycle_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get("/rebalance/proposals")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED"


def test_proposal_async_create_and_operation_lookup_roundtrip() -> None:
    payload = _base_create_payload("pf_integration_proposal_async_1")
    headers = {
        "Idempotency-Key": "integration-proposal-async-create-1",
        "X-Correlation-Id": "corr-integration-proposal-async-create-1",
    }
    with TestClient(app) as client:
        accepted = client.post("/rebalance/proposals/async", json=payload, headers=headers)
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        by_operation = client.get(f"/rebalance/proposals/operations/{operation_id}")
        by_correlation = client.get(
            "/rebalance/proposals/operations/by-correlation/corr-integration-proposal-async-create-1"
        )

    assert by_operation.status_code == 200
    assert by_correlation.status_code == 200
    assert by_operation.json()["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id
    assert by_operation.json()["status"] in {"SUCCEEDED", "PENDING"}


def test_proposal_async_version_roundtrip() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/rebalance/proposals",
            json=_base_create_payload("pf_integration_proposal_async_2"),
            headers={"Idempotency-Key": "integration-proposal-async-version-create-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        accepted = client.post(
            f"/rebalance/proposals/{proposal_id}/versions/async",
            json={
                "created_by": "advisor_integration",
                "metadata": {"title": "Async version"},
                "simulate_request": _base_create_payload("pf_integration_proposal_async_2")[
                    "simulate_request"
                ],
            },
            headers={"X-Correlation-Id": "corr-integration-proposal-async-version-1"},
        )
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        operation = client.get(f"/rebalance/proposals/operations/{operation_id}")

    assert operation.status_code == 200
    assert operation.json()["operation_id"] == operation_id
    assert operation.json()["status"] in {"SUCCEEDED", "PENDING"}


def test_proposal_async_operations_disabled_by_feature_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROPOSAL_ASYNC_OPERATIONS_ENABLED", "false")
    payload = _base_create_payload("pf_integration_proposal_async_disabled")
    with TestClient(app) as client:
        response = client.post(
            "/rebalance/proposals/async",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-async-disabled-1"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATIONS_DISABLED"


def test_proposal_async_operation_not_found_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/rebalance/proposals/operations/pop_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"


@pytest.mark.parametrize(
    ("env_name", "env_value", "path", "expected_detail"),
    [
        (
            "PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED",
            "false",
            "/rebalance/proposals",
            "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED",
        ),
        (
            "PROPOSAL_SUPPORT_APIS_ENABLED",
            "false",
            "/rebalance/proposals/p_missing/approvals",
            "PROPOSAL_SUPPORT_APIS_DISABLED",
        ),
        (
            "PROPOSAL_ASYNC_OPERATIONS_ENABLED",
            "false",
            "/rebalance/proposals/operations/pop_missing",
            "PROPOSAL_ASYNC_OPERATIONS_DISABLED",
        ),
    ],
)
def test_proposal_feature_flag_guard_matrix(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
    path: str,
    expected_detail: str,
) -> None:
    monkeypatch.setenv(env_name, env_value)
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/rebalance/proposals/p_missing", "PROPOSAL_NOT_FOUND"),
        ("/rebalance/proposals/p_missing/versions/1", "PROPOSAL_VERSION_NOT_FOUND"),
        ("/rebalance/proposals/p_missing/workflow-events", "PROPOSAL_NOT_FOUND"),
        ("/rebalance/proposals/p_missing/approvals", "PROPOSAL_NOT_FOUND"),
        ("/rebalance/proposals/p_missing/lineage", "PROPOSAL_NOT_FOUND"),
    ],
)
def test_proposal_not_found_matrix(path: str, expected_detail: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


def test_proposal_idempotency_lookup_not_found_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/rebalance/proposals/idempotency/idem_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND"


@pytest.mark.parametrize(
    "path",
    [
        "/rebalance/proposals/p_missing/workflow-events",
        "/rebalance/proposals/p_missing/approvals",
        "/rebalance/proposals/p_missing/lineage",
        "/rebalance/proposals/idempotency/idem_missing",
    ],
)
def test_proposal_support_api_guard_matrix(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setenv("PROPOSAL_SUPPORT_APIS_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_SUPPORT_APIS_DISABLED"


@pytest.mark.parametrize(
    "path",
    [
        "/rebalance/proposals",
        "/rebalance/proposals/p_missing",
        "/rebalance/proposals/p_missing/versions/1",
        "/rebalance/proposals/p_missing/workflow-events",
        "/rebalance/proposals/p_missing/approvals",
        "/rebalance/proposals/p_missing/lineage",
        "/rebalance/proposals/operations/pop_missing",
        "/rebalance/proposals/operations/by-correlation/corr_missing",
    ],
)
def test_proposal_lifecycle_guard_matrix(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setenv("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED"


@pytest.mark.parametrize(
    "path",
    [
        "/rebalance/proposals/operations/pop_missing",
        "/rebalance/proposals/operations/by-correlation/corr_missing",
    ],
)
def test_proposal_async_api_guard_matrix(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setenv("PROPOSAL_ASYNC_OPERATIONS_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATIONS_DISABLED"


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/rebalance/proposals/p_missing/transitions", "PROPOSAL_NOT_FOUND"),
        ("/rebalance/proposals/p_missing/approvals", "PROPOSAL_NOT_FOUND"),
    ],
)
def test_proposal_post_not_found_matrix(path: str, expected_detail: str) -> None:
    payload = (
        {
            "event_type": "SUBMITTED_FOR_RISK_REVIEW",
            "actor_id": "advisor_integration",
            "expected_state": "DRAFT",
            "reason": {"comment": "integration submit"},
        }
        if path.endswith("/transitions")
        else {
            "approval_type": "CLIENT_CONSENT",
            "approved": True,
            "actor_id": "reviewer_integration",
            "details": {"comment": "approved"},
        }
    )

    with TestClient(app) as client:
        response = client.post(path, json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail
