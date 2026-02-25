import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app
from src.api.routers import proposals as proposals_router
from src.api.routers.proposals import reset_proposal_workflow_service_for_tests


def _base_create_payload(portfolio_id: str = "pf_lifecycle_1") -> dict:
    return {
        "created_by": "advisor_1",
        "metadata": {
            "title": "Lifecycle proposal",
            "advisor_notes": "Advisor notes",
            "jurisdiction": "SG",
            "mandate_id": "mandate_1",
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


def _create(client: TestClient, idempotency_key: str, payload: dict | None = None) -> dict:
    response = client.post(
        "/rebalance/proposals",
        json=payload or _base_create_payload(),
        headers={"Idempotency-Key": idempotency_key},
    )
    assert response.status_code == 200
    return response.json()


def setup_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()


def test_create_proposal_persists_immutable_version_and_created_event():
    with TestClient(app) as client:
        body = _create(client, "lifecycle-create-1")

        assert body["proposal"]["current_state"] == "DRAFT"
        assert body["proposal"]["current_version_no"] == 1
        assert body["version"]["version_no"] == 1
        assert body["version"]["status_at_creation"] == "READY"
        assert body["version"]["artifact_hash"].startswith("sha256:")
        assert body["latest_workflow_event"]["event_type"] == "CREATED"


def test_get_proposal_repository_maps_runtime_and_value_errors(monkeypatch):
    reset_proposal_workflow_service_for_tests()

    def _raise_runtime():
        raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")

    monkeypatch.setattr(proposals_router.proposals_config, "build_repository", _raise_runtime)
    with pytest.raises(HTTPException) as runtime_exc:
        proposals_router.get_proposal_repository()
    assert runtime_exc.value.status_code == 503
    assert runtime_exc.value.detail == "PROPOSAL_POSTGRES_DSN_REQUIRED"

    reset_proposal_workflow_service_for_tests()

    def _raise_value():
        raise ValueError("invalid")

    monkeypatch.setattr(proposals_router.proposals_config, "build_repository", _raise_value)
    with pytest.raises(HTTPException) as value_exc:
        proposals_router.get_proposal_repository()
    assert value_exc.value.status_code == 503
    assert value_exc.value.detail == "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def test_proposal_repository_backend_init_errors_return_503(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
        monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)
        reset_proposal_workflow_service_for_tests()

        missing_dsn = client.get("/rebalance/proposals")
        assert missing_dsn.status_code == 503
        assert missing_dsn.json()["detail"] == "PROPOSAL_POSTGRES_DSN_REQUIRED"

        monkeypatch.setenv(
            "PROPOSAL_POSTGRES_DSN",
            "postgresql://user:pass@localhost:5432/proposals",
        )
        monkeypatch.setattr(
            "src.api.routers.proposals_config.PostgresProposalRepository",
            lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("boom")),
        )
        reset_proposal_workflow_service_for_tests()
        not_implemented = client.get("/rebalance/proposals")
        assert not_implemented.status_code == 503
        assert not_implemented.json()["detail"] == "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def test_proposal_repository_unexpected_init_error_mapped_to_503(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(
            "src.api.routers.proposals.proposals_config.build_repository",
            lambda: (_ for _ in ()).throw(ValueError("boom")),
        )
        reset_proposal_workflow_service_for_tests()

        response = client.get("/rebalance/proposals")
        assert response.status_code == 503
        assert response.json()["detail"] == "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def test_proposal_supportability_config_defaults():
    with TestClient(app) as client:
        response = client.get("/rebalance/proposals/supportability/config")
        assert response.status_code == 200
        body = response.json()
        assert body["store_backend"] == "POSTGRES"
        assert body["backend_ready"] is True
        assert body["backend_init_error"] is None
        assert body["lifecycle_enabled"] is True
        assert body["support_apis_enabled"] is True
        assert body["async_operations_enabled"] is True
        assert body["store_evidence_bundle"] is True
        assert body["require_expected_state"] is True
        assert body["allow_portfolio_id_change_on_new_version"] is False
        assert body["require_proposal_simulation_flag"] is True


def test_proposal_supportability_config_reports_backend_error(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setenv("PROPOSAL_STORE_BACKEND", "POSTGRES")
        monkeypatch.delenv("PROPOSAL_POSTGRES_DSN", raising=False)

        response = client.get("/rebalance/proposals/supportability/config")
        assert response.status_code == 200
        body = response.json()
        assert body["store_backend"] == "POSTGRES"
        assert body["backend_ready"] is False
        assert body["backend_init_error"] == "PROPOSAL_POSTGRES_DSN_REQUIRED"


def test_proposal_supportability_config_reports_unexpected_backend_error(monkeypatch):
    with TestClient(app) as client:
        monkeypatch.setattr(
            "src.api.routers.proposals.proposals_config.build_repository",
            lambda: (_ for _ in ()).throw(ValueError("boom")),
        )
        response = client.get("/rebalance/proposals/supportability/config")
        assert response.status_code == 200
        body = response.json()
        assert body["backend_ready"] is False
        assert body["backend_init_error"] == "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def test_create_proposal_idempotency_reuses_existing_proposal_and_detects_conflict():
    with TestClient(app) as client:
        first = _create(client, "lifecycle-create-2")
        second = _create(client, "lifecycle-create-2")

        assert first == second

        changed = _base_create_payload()
        changed["simulate_request"]["proposed_cash_flows"] = [{"currency": "USD", "amount": "777"}]
        conflict = client.post(
            "/rebalance/proposals",
            json=changed,
            headers={"Idempotency-Key": "lifecycle-create-2"},
        )
        assert conflict.status_code == 409
        assert "IDEMPOTENCY_KEY_CONFLICT" in conflict.json()["detail"]


def test_get_list_and_version_include_and_hide_evidence():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-3")
        proposal_id = created["proposal"]["proposal_id"]

        listed = client.get("/rebalance/proposals", params={"portfolio_id": "pf_lifecycle_1"})
        assert listed.status_code == 200
        assert listed.json()["items"][0]["proposal_id"] == proposal_id

        detail = client.get(
            f"/rebalance/proposals/{proposal_id}", params={"include_evidence": False}
        )
        assert detail.status_code == 200
        assert detail.json()["current_version"]["evidence_bundle"] == {}

        version = client.get(
            f"/rebalance/proposals/{proposal_id}/versions/1",
            params={"include_evidence": True},
        )
        assert version.status_code == 200
        assert version.json()["evidence_bundle"]["hashes"]["artifact_hash"].startswith("sha256:")


def test_create_version_increments_version_and_preserves_state():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-4")
        proposal_id = created["proposal"]["proposal_id"]

        version_payload = {
            "created_by": "advisor_2",
            "simulate_request": _base_create_payload()["simulate_request"],
        }
        version_payload["simulate_request"]["proposed_trades"] = [
            {"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "3"}
        ]

        response = client.post(f"/rebalance/proposals/{proposal_id}/versions", json=version_payload)
        assert response.status_code == 200
        body = response.json()
        assert body["proposal"]["current_version_no"] == 2
        assert body["proposal"]["current_state"] == "DRAFT"
        assert body["version"]["version_no"] == 2
        assert body["latest_workflow_event"]["event_type"] == "NEW_VERSION_CREATED"


def test_transition_requires_expected_state_and_rejects_invalid_transition():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-5")
        proposal_id = created["proposal"]["proposal_id"]

        missing_expected = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_1",
                "reason": {"comment": "submit"},
            },
        )
        assert missing_expected.status_code == 409
        assert "expected_state is required" in missing_expected.json()["detail"]

        invalid = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "EXECUTED",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {"comment": "invalid"},
            },
        )
        assert invalid.status_code == 422
        assert invalid.json()["detail"] == "INVALID_TRANSITION"


def test_workflow_transitions_and_approvals_happy_path_to_executed():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-6")
        proposal_id = created["proposal"]["proposal_id"]

        to_compliance = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {"comment": "needs compliance"},
                "related_version_no": 1,
            },
        )
        assert to_compliance.status_code == 200
        assert to_compliance.json()["current_state"] == "COMPLIANCE_REVIEW"

        compliance_approved = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "COMPLIANCE",
                "approved": True,
                "actor_id": "compliance_user",
                "expected_state": "COMPLIANCE_REVIEW",
                "details": {"comment": "ok"},
                "related_version_no": 1,
            },
        )
        assert compliance_approved.status_code == 200
        assert compliance_approved.json()["current_state"] == "AWAITING_CLIENT_CONSENT"
        assert compliance_approved.json()["approval"]["approval_type"] == "COMPLIANCE"

        consent = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "CLIENT_CONSENT",
                "approved": True,
                "actor_id": "client_1",
                "expected_state": "AWAITING_CLIENT_CONSENT",
                "details": {"channel": "IN_PERSON"},
                "related_version_no": 1,
            },
        )
        assert consent.status_code == 200
        assert consent.json()["current_state"] == "EXECUTION_READY"

        executed = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "EXECUTED",
                "actor_id": "ops_1",
                "expected_state": "EXECUTION_READY",
                "reason": {"execution_id": "oms_123"},
                "related_version_no": 1,
            },
        )
        assert executed.status_code == 200
        assert executed.json()["current_state"] == "EXECUTED"


def test_workflow_transitions_happy_path_via_risk_to_execution_ready():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-risk-happy")
        proposal_id = created["proposal"]["proposal_id"]

        to_risk = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {"comment": "risk first"},
                "related_version_no": 1,
            },
        )
        assert to_risk.status_code == 200
        assert to_risk.json()["current_state"] == "RISK_REVIEW"

        risk_approved = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_user",
                "expected_state": "RISK_REVIEW",
                "details": {"ticket": "risk_1"},
                "related_version_no": 1,
            },
        )
        assert risk_approved.status_code == 200
        assert risk_approved.json()["current_state"] == "AWAITING_CLIENT_CONSENT"
        assert risk_approved.json()["latest_workflow_event"]["event_type"] == "RISK_APPROVED"

        consent = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "CLIENT_CONSENT",
                "approved": True,
                "actor_id": "client_1",
                "expected_state": "AWAITING_CLIENT_CONSENT",
                "details": {"channel": "DIGITAL"},
                "related_version_no": 1,
            },
        )
        assert consent.status_code == 200
        assert consent.json()["current_state"] == "EXECUTION_READY"


def test_workflow_rejection_path_transitions_to_rejected_terminal_state():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-rejected")
        proposal_id = created["proposal"]["proposal_id"]

        to_risk = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {"comment": "risk first"},
            },
        )
        assert to_risk.status_code == 200
        assert to_risk.json()["current_state"] == "RISK_REVIEW"

        rejected = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "RISK",
                "approved": False,
                "actor_id": "risk_user",
                "expected_state": "RISK_REVIEW",
                "details": {"comment": "client not suitable"},
            },
        )
        assert rejected.status_code == 200
        assert rejected.json()["current_state"] == "REJECTED"
        assert rejected.json()["latest_workflow_event"]["event_type"] == "REJECTED"

        invalid_after_terminal = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "REJECTED",
                "reason": {"comment": "should fail"},
            },
        )
        assert invalid_after_terminal.status_code == 422
        assert invalid_after_terminal.json()["detail"] == "INVALID_TRANSITION"


def test_approval_requires_matching_expected_state():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-create-7")
        proposal_id = created["proposal"]["proposal_id"]

        approval = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "CLIENT_CONSENT",
                "approved": True,
                "actor_id": "client_1",
                "expected_state": "RISK_REVIEW",
                "details": {},
            },
        )
        assert approval.status_code == 409
        assert "STATE_CONFLICT" in approval.json()["detail"]


def test_lifecycle_router_returns_404_when_disabled(monkeypatch):
    monkeypatch.setenv("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", "false")
    reset_proposal_workflow_service_for_tests()
    with TestClient(app) as client:
        response = client.get("/rebalance/proposals")
    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED"


def test_create_proposal_returns_422_when_simulation_flag_disabled():
    with TestClient(app) as client:
        payload = _base_create_payload()
        payload["simulate_request"]["options"] = {"enable_proposal_simulation": False}
        response = client.post(
            "/rebalance/proposals",
            json=payload,
            headers={"Idempotency-Key": "lifecycle-create-disabled"},
        )
    assert response.status_code == 422
    assert "PROPOSAL_SIMULATION_DISABLED" in response.json()["detail"]


def test_get_and_get_version_return_404_for_missing_proposal():
    with TestClient(app) as client:
        proposal_response = client.get("/rebalance/proposals/pp_missing_1")
        version_response = client.get("/rebalance/proposals/pp_missing_1/versions/1")
    assert proposal_response.status_code == 404
    assert version_response.status_code == 404


def test_create_version_not_found_and_context_validation_paths():
    with TestClient(app) as client:
        version_payload = {
            "created_by": "advisor_2",
            "simulate_request": _base_create_payload()["simulate_request"],
        }

        missing = client.post("/rebalance/proposals/pp_missing_2/versions", json=version_payload)
        assert missing.status_code == 404

        created = _create(client, "lifecycle-create-ctx-1")
        proposal_id = created["proposal"]["proposal_id"]
        version_payload["simulate_request"]["portfolio_snapshot"]["portfolio_id"] = "pf_other"
        invalid = client.post(f"/rebalance/proposals/{proposal_id}/versions", json=version_payload)
        assert invalid.status_code == 422
        assert invalid.json()["detail"] == "PORTFOLIO_CONTEXT_MISMATCH"


def test_transition_and_approval_not_found_and_invalid_approval_state_paths():
    with TestClient(app) as client:
        missing_transition = client.post(
            "/rebalance/proposals/pp_missing_3/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {},
            },
        )
        assert missing_transition.status_code == 404

        missing_approval = client.post(
            "/rebalance/proposals/pp_missing_3/approvals",
            json={
                "approval_type": "RISK",
                "approved": True,
                "actor_id": "risk_1",
                "expected_state": "RISK_REVIEW",
                "details": {},
            },
        )
        assert missing_approval.status_code == 404

        created = _create(client, "lifecycle-create-approval-422")
        proposal_id = created["proposal"]["proposal_id"]
        invalid_state = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "COMPLIANCE",
                "approved": True,
                "actor_id": "compliance_1",
                "expected_state": "DRAFT",
                "details": {},
            },
        )
        assert invalid_state.status_code == 422
        assert invalid_state.json()["detail"] == "INVALID_APPROVAL_STATE"


def test_support_endpoints_return_timeline_approvals_lineage_and_idempotency():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-support-1")
        proposal_id = created["proposal"]["proposal_id"]

        submit = client.post(
            f"/rebalance/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_COMPLIANCE_REVIEW",
                "actor_id": "advisor_1",
                "expected_state": "DRAFT",
                "reason": {"comment": "submit"},
                "related_version_no": 1,
            },
        )
        assert submit.status_code == 200
        approval = client.post(
            f"/rebalance/proposals/{proposal_id}/approvals",
            json={
                "approval_type": "COMPLIANCE",
                "approved": True,
                "actor_id": "compliance_1",
                "expected_state": "COMPLIANCE_REVIEW",
                "details": {"ticket": "cmp_1"},
                "related_version_no": 1,
            },
        )
        assert approval.status_code == 200

        timeline = client.get(f"/rebalance/proposals/{proposal_id}/workflow-events")
        assert timeline.status_code == 200
        timeline_body = timeline.json()
        assert timeline_body["proposal_id"] == proposal_id
        assert len(timeline_body["events"]) >= 3
        assert timeline_body["events"][0]["event_type"] == "CREATED"

        approvals = client.get(f"/rebalance/proposals/{proposal_id}/approvals")
        assert approvals.status_code == 200
        approvals_body = approvals.json()
        assert approvals_body["proposal_id"] == proposal_id
        assert len(approvals_body["approvals"]) == 1
        assert approvals_body["approvals"][0]["approval_type"] == "COMPLIANCE"

        lineage = client.get(f"/rebalance/proposals/{proposal_id}/lineage")
        assert lineage.status_code == 200
        lineage_body = lineage.json()
        assert lineage_body["proposal"]["proposal_id"] == proposal_id
        assert lineage_body["versions"][0]["version_no"] == 1
        assert lineage_body["versions"][0]["artifact_hash"].startswith("sha256:")

        idem_lookup = client.get("/rebalance/proposals/idempotency/lifecycle-support-1")
        assert idem_lookup.status_code == 200
        idem_body = idem_lookup.json()
        assert idem_body["idempotency_key"] == "lifecycle-support-1"
        assert idem_body["proposal_id"] == proposal_id
        assert idem_body["proposal_version_no"] == 1


def test_support_endpoints_404_for_missing_entities():
    with TestClient(app) as client:
        missing_timeline = client.get("/rebalance/proposals/pp_missing_support/workflow-events")
        assert missing_timeline.status_code == 404

        missing_approvals = client.get("/rebalance/proposals/pp_missing_support/approvals")
        assert missing_approvals.status_code == 404

        missing_lineage = client.get("/rebalance/proposals/pp_missing_support/lineage")
        assert missing_lineage.status_code == 404

        missing_idempotency = client.get("/rebalance/proposals/idempotency/missing-idem")
        assert missing_idempotency.status_code == 404
        assert missing_idempotency.json()["detail"] == "PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND"


def test_support_endpoints_return_404_when_support_apis_disabled(monkeypatch):
    monkeypatch.setenv("PROPOSAL_SUPPORT_APIS_ENABLED", "false")
    reset_proposal_workflow_service_for_tests()
    with TestClient(app) as client:
        created = _create(client, "lifecycle-support-disabled")
        proposal_id = created["proposal"]["proposal_id"]

        timeline = client.get(f"/rebalance/proposals/{proposal_id}/workflow-events")
        assert timeline.status_code == 404
        assert timeline.json()["detail"] == "PROPOSAL_SUPPORT_APIS_DISABLED"


def test_async_create_and_lookup_by_operation_and_correlation():
    with TestClient(app) as client:
        payload = _base_create_payload()
        accepted = client.post(
            "/rebalance/proposals/async",
            json=payload,
            headers={
                "Idempotency-Key": "lifecycle-async-create-1",
                "X-Correlation-Id": "corr-async-create-1",
            },
        )
        assert accepted.status_code == 202
        accepted_body = accepted.json()
        assert accepted_body["operation_type"] == "CREATE_PROPOSAL"
        assert accepted_body["correlation_id"] == "corr-async-create-1"

        operation_id = accepted_body["operation_id"]
        by_operation = client.get(f"/rebalance/proposals/operations/{operation_id}")
        assert by_operation.status_code == 200
        op_body = by_operation.json()
        assert op_body["status"] == "SUCCEEDED"
        assert op_body["result"]["proposal"]["proposal_id"].startswith("pp_")

        by_correlation = client.get(
            "/rebalance/proposals/operations/by-correlation/corr-async-create-1"
        )
        assert by_correlation.status_code == 200
        assert by_correlation.json()["operation_id"] == operation_id

        missing_by_correlation = client.get(
            "/rebalance/proposals/operations/by-correlation/corr-missing"
        )
        assert missing_by_correlation.status_code == 404
        assert missing_by_correlation.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"


def test_async_create_version_and_lookup():
    with TestClient(app) as client:
        created = _create(client, "lifecycle-async-version-base")
        proposal_id = created["proposal"]["proposal_id"]
        payload = {
            "created_by": "advisor_2",
            "simulate_request": _base_create_payload()["simulate_request"],
        }
        payload["simulate_request"]["proposed_trades"] = [
            {"side": "BUY", "instrument_id": "EQ_NEW", "quantity": "4"}
        ]
        accepted = client.post(
            f"/rebalance/proposals/{proposal_id}/versions/async",
            json=payload,
            headers={"X-Correlation-Id": "corr-async-version-1"},
        )
        assert accepted.status_code == 202
        operation_id = accepted.json()["operation_id"]

        operation = client.get(f"/rebalance/proposals/operations/{operation_id}")
        assert operation.status_code == 200
        body = operation.json()
        assert body["operation_type"] == "CREATE_PROPOSAL_VERSION"
        assert body["status"] == "SUCCEEDED"
        assert body["result"]["proposal"]["current_version_no"] == 2


def test_async_operation_endpoints_return_404_when_disabled(monkeypatch):
    monkeypatch.setenv("PROPOSAL_ASYNC_OPERATIONS_ENABLED", "false")
    reset_proposal_workflow_service_for_tests()
    with TestClient(app) as client:
        payload = _base_create_payload()
        response = client.post(
            "/rebalance/proposals/async",
            json=payload,
            headers={"Idempotency-Key": "lifecycle-async-disabled"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATIONS_DISABLED"


def test_async_operation_lookup_returns_404_for_missing_operation():
    with TestClient(app) as client:
        missing = client.get("/rebalance/proposals/operations/pop_missing")
        assert missing.status_code == 404
        assert missing.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"
