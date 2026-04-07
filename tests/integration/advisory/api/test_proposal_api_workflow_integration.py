from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from src.api.main import PROPOSAL_IDEMPOTENCY_CACHE, app
from src.api.proposals.router import reset_proposal_workflow_service_for_tests
from src.api.services.workspace_service import reset_workspace_sessions_for_tests
from src.integrations.lotus_core.context_resolution import LotusCoreContextResolutionError
from tests.shared.stateful_context_builders import (
    build_resolved_stateful_context,
    build_tradeable_universe_stateful_context,
)


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
    reset_workspace_sessions_for_tests()


def teardown_function() -> None:
    PROPOSAL_IDEMPOTENCY_CACHE.clear()
    reset_proposal_workflow_service_for_tests()
    reset_workspace_sessions_for_tests()


def _resolved_stateful_context(portfolio_id: str, as_of: str) -> dict:
    payload = _base_create_payload(portfolio_id=portfolio_id)["simulate_request"]
    return build_resolved_stateful_context(
        portfolio_id,
        as_of,
        positions=payload["portfolio_snapshot"]["positions"],
        cash_amount=payload["portfolio_snapshot"]["cash_balances"][0]["amount"],
        prices=payload["market_data_snapshot"]["prices"],
        shelf_entries=payload["shelf_entries"],
    )


def _resolved_stateful_context_with_tradeable_universe(
    portfolio_id: str,
    as_of: str,
) -> dict:
    return build_tradeable_universe_stateful_context(portfolio_id, as_of)


def _flaky_stateful_resolver_factory(
    *,
    portfolio_id: str,
    as_of: str,
    use_tradeable_universe: bool = False,
):
    state = {"calls": 0}

    def _resolver(_stateful_input):
        state["calls"] += 1
        if state["calls"] == 1:
            raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")
        if use_tradeable_universe:
            return _resolved_stateful_context_with_tradeable_universe(
                portfolio_id=portfolio_id,
                as_of=as_of,
            )
        return _resolved_stateful_context(portfolio_id=portfolio_id, as_of=as_of)

    return _resolver, state


def _submit_async_create(
    client: TestClient,
    *,
    payload: dict,
    idempotency_key: str,
    correlation_id: str,
) -> tuple[str, dict]:
    accepted = client.post(
        "/advisory/proposals/async",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
            "X-Correlation-Id": correlation_id,
        },
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    operation = client.get(f"/advisory/proposals/operations/{operation_id}")
    assert operation.status_code == 200
    return operation_id, operation.json()


def _submit_async_version(
    client: TestClient,
    *,
    proposal_id: str,
    payload: dict,
    correlation_id: str,
) -> tuple[str, dict]:
    accepted = client.post(
        f"/advisory/proposals/{proposal_id}/versions/async",
        json=payload,
        headers={"X-Correlation-Id": correlation_id},
    )
    assert accepted.status_code == 202
    operation_id = accepted.json()["operation_id"]
    operation = client.get(f"/advisory/proposals/operations/{operation_id}")
    assert operation.status_code == 200
    return operation_id, operation.json()


def test_proposal_create_list_get_and_version_roundtrip() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload(),
            headers={"Idempotency-Key": "integration-proposal-create-1"},
        )
        assert created.status_code == 200
        created_body = created.json()
        proposal_id = created_body["proposal"]["proposal_id"]

        listed = client.get(
            "/advisory/proposals",
            params={"portfolio_id": "pf_integration_proposal_1"},
        )
        detail = client.get(f"/advisory/proposals/{proposal_id}")
        version = client.get(f"/advisory/proposals/{proposal_id}/versions/1")
        workflow_events = client.get(f"/advisory/proposals/{proposal_id}/workflow-events")

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
            "/advisory/proposals",
            json=_base_create_payload("pf_integration_proposal_2"),
            headers={"Idempotency-Key": "integration-proposal-submit-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        submit = client.post(
            f"/advisory/proposals/{proposal_id}/transitions",
            json={
                "event_type": "SUBMITTED_FOR_RISK_REVIEW",
                "actor_id": "advisor_integration",
                "expected_state": "DRAFT",
                "reason": {"comment": "integration submit"},
            },
        )
        approvals = client.get(f"/advisory/proposals/{proposal_id}/approvals")
        lineage = client.get(f"/advisory/proposals/{proposal_id}/lineage")

    assert submit.status_code == 200
    assert approvals.status_code == 200
    assert lineage.status_code == 200
    assert submit.json()["current_state"] == "RISK_REVIEW"
    assert approvals.json()["proposal"]["proposal_id"] == proposal_id
    assert approvals.json()["approval_count"] == 0
    assert approvals.json()["latest_approval_at"] is None
    assert lineage.json()["proposal"]["proposal_id"] == proposal_id
    assert lineage.json()["version_count"] == 1
    assert lineage.json()["lineage_complete"] is True


def test_stateful_proposal_create_roundtrip_persists_context_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context_with_tradeable_universe(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )

    payload = {
        "created_by": "advisor_stateful_integration",
        "metadata": {
            "title": "Stateful integration proposal",
            "advisor_notes": "stateful integration coverage",
            "jurisdiction": "SG",
        },
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_stateful_integration_1",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_stateful_integration_1",
        },
    }

    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-stateful-create-1"},
        )
        assert created.status_code == 200
        created_body = created.json()
        proposal_id = created_body["proposal"]["proposal_id"]

        detail = client.get(f"/advisory/proposals/{proposal_id}")
        version = client.get(f"/advisory/proposals/{proposal_id}/versions/1")

    assert detail.status_code == 200
    assert version.status_code == 200
    assert created_body["proposal"]["portfolio_id"] == "pf_stateful_integration_1"
    assert created_body["proposal"]["mandate_id"] == "mandate_stateful_integration_1"
    assert (
        created_body["version"]["evidence_bundle"]["context_resolution"]["input_mode"] == "stateful"
    )
    assert (
        created_body["version"]["evidence_bundle"]["context_resolution"]["resolution_source"]
        == "LOTUS_CORE"
    )
    assert version.json()["proposal_result"]["lineage"]["portfolio_snapshot_id"] == (
        "ps_pf_stateful_integration_1_2026-03-25"
    )


def test_stateful_workspace_handoff_roundtrip_persists_replay_continuity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )

    create_payload = {
        "workspace_name": "Stateful integration workspace",
        "created_by": "advisor_stateful_integration",
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_stateful_workspace_1",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_stateful_workspace_1",
        },
    }

    with TestClient(app) as client:
        created = client.post("/advisory/workspaces", json=create_payload)
        assert created.status_code == 201
        workspace_id = created.json()["workspace"]["workspace_id"]

        add_trade = client.post(
            f"/advisory/workspaces/{workspace_id}/draft-actions",
            json={
                "actor_id": "advisor_stateful_integration",
                "action_type": "ADD_TRADE",
                "trade": {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_NEW",
                    "quantity": "3",
                },
            },
        )
        assert add_trade.status_code == 200

        saved = client.post(
            f"/advisory/workspaces/{workspace_id}/save",
            json={
                "saved_by": "advisor_stateful_integration",
                "version_label": "Stateful integration baseline",
            },
        )
        assert saved.status_code == 200
        workspace_version_id = saved.json()["saved_version"]["workspace_version_id"]

        handoff = client.post(
            f"/advisory/workspaces/{workspace_id}/handoff",
            json={"handoff_by": "advisor_stateful_integration"},
            headers={"Idempotency-Key": "integration-workspace-stateful-handoff-1"},
        )
        assert handoff.status_code == 200
        handoff_body = handoff.json()

        replay = client.get(
            f"/advisory/workspaces/{workspace_id}/saved-versions/"
            f"{workspace_version_id}/replay-evidence"
        )
        proposal_id = handoff_body["proposal"]["proposal"]["proposal_id"]
        proposal_version = client.get(f"/advisory/proposals/{proposal_id}/versions/1")

    assert replay.status_code == 200
    replay_body = replay.json()
    proposal_version_body = proposal_version.json()
    assert handoff_body["proposal"]["proposal"]["lifecycle_origin"] == "WORKSPACE_HANDOFF"
    assert handoff_body["proposal"]["proposal"]["mandate_id"] == "mandate_stateful_workspace_1"
    assert (
        handoff_body["proposal"]["version"]["proposal_result"]["intents"][-1]["instrument_id"]
        == "EQ_NEW"
    )
    assert replay_body["subject"]["proposal_id"] == proposal_id
    assert replay_body["subject"]["proposal_version_no"] == 1
    assert replay_body["resolved_context"]["portfolio_id"] == "pf_stateful_workspace_1"
    assert proposal_version_body["evidence_bundle"]["context_resolution"]["input_mode"] == (
        "stateful"
    )
    assert (
        proposal_version_body["evidence_bundle"]["replay_lineage"]["workspace_id"] == workspace_id
    )
    assert (
        proposal_version_body["evidence_bundle"]["replay_lineage"]["workspace_version_id"]
        == workspace_version_id
    )


def test_proposal_idempotency_lookup_roundtrip() -> None:
    idempotency_key = "integration-proposal-idem-lookup-1"
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_integration_proposal_3"),
            headers={"Idempotency-Key": idempotency_key},
        )
        assert created.status_code == 200

        lookup = client.get(f"/advisory/proposals/idempotency/{idempotency_key}")

    assert lookup.status_code == 200
    assert lookup.json()["idempotency_key"] == idempotency_key


def test_proposal_support_endpoints_disabled_by_feature_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_integration_proposal_4"),
            headers={"Idempotency-Key": "integration-proposal-support-disabled-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        monkeypatch.setenv("PROPOSAL_SUPPORT_APIS_ENABLED", "false")
        approvals = client.get(f"/advisory/proposals/{proposal_id}/approvals")

    assert approvals.status_code == 404
    assert approvals.json()["detail"] == "PROPOSAL_SUPPORT_APIS_DISABLED"


def test_proposal_lifecycle_disabled_by_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", "false")
    with TestClient(app) as client:
        response = client.get("/advisory/proposals")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED"


def test_proposal_async_create_and_operation_lookup_roundtrip() -> None:
    payload = _base_create_payload("pf_integration_proposal_async_1")
    with TestClient(app) as client:
        operation_id, operation_body = _submit_async_create(
            client,
            payload=payload,
            idempotency_key="integration-proposal-async-create-1",
            correlation_id="corr-integration-proposal-async-create-1",
        )
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/corr-integration-proposal-async-create-1"
        )

    assert by_correlation.status_code == 200
    assert operation_body["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id
    assert operation_body["status"] in {"SUCCEEDED", "PENDING"}
    assert operation_body["attempt_count"] >= 1


def test_stateful_async_create_roundtrip_persists_context_and_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context_with_tradeable_universe(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )
    payload = {
        "created_by": "advisor_stateful_async",
        "metadata": {
            "title": "Stateful async create",
            "advisor_notes": "async stateful integration coverage",
            "jurisdiction": "SG",
        },
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_async_stateful_integration_1",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_async_stateful_1",
        },
    }
    with TestClient(app) as client:
        operation_id, operation_body = _submit_async_create(
            client,
            payload=payload,
            idempotency_key="integration-proposal-async-stateful-create-1",
            correlation_id="corr-integration-proposal-async-stateful-create-1",
        )
        assert operation_body["status"] == "SUCCEEDED"
        proposal_id = operation_body["result"]["proposal"]["proposal_id"]
        version_no = operation_body["result"]["version"]["version_no"]

        proposal_version = client.get(f"/advisory/proposals/{proposal_id}/versions/{version_no}")
        async_replay = client.get(f"/advisory/proposals/operations/{operation_id}/replay-evidence")
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-create-1"
        )

    assert proposal_version.status_code == 200
    assert async_replay.status_code == 200
    assert by_correlation.status_code == 200
    proposal_version_body = proposal_version.json()
    async_replay_body = async_replay.json()
    assert by_correlation.json()["operation_id"] == operation_id
    assert operation_body["result"]["proposal"]["portfolio_id"] == "pf_async_stateful_integration_1"
    assert operation_body["result"]["proposal"]["mandate_id"] == "mandate_async_stateful_1"
    assert (
        proposal_version_body["evidence_bundle"]["context_resolution"]["input_mode"] == "stateful"
    )
    assert proposal_version_body["evidence_bundle"]["context_resolution"]["resolution_source"] == (
        "LOTUS_CORE"
    )
    assert async_replay_body["subject"]["proposal_id"] == proposal_id
    assert async_replay_body["subject"]["proposal_version_no"] == version_no
    assert (
        async_replay_body["resolved_context"]["portfolio_id"] == "pf_async_stateful_integration_1"
    )
    assert (
        async_replay_body["evidence"]["context_resolution"]["resolved_context"][
            "portfolio_snapshot_id"
        ]
        == "ps_pf_async_stateful_integration_1_2026-03-25"
    )


def test_proposal_async_version_roundtrip() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_integration_proposal_async_2"),
            headers={"Idempotency-Key": "integration-proposal-async-version-create-1"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        operation_id, operation_body = _submit_async_version(
            client,
            proposal_id=proposal_id,
            payload={
                "created_by": "advisor_integration",
                "metadata": {"title": "Async version"},
                "simulate_request": _base_create_payload("pf_integration_proposal_async_2")[
                    "simulate_request"
                ],
            },
            correlation_id="corr-integration-proposal-async-version-1",
        )
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/corr-integration-proposal-async-version-1"
        )

    assert by_correlation.status_code == 200
    assert operation_body["operation_id"] == operation_id
    assert by_correlation.json()["operation_id"] == operation_id
    assert operation_body["status"] in {"SUCCEEDED", "PENDING"}
    assert operation_body["attempt_count"] >= 1


def test_stateful_async_version_roundtrip_preserves_replay_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        lambda stateful_input: _resolved_stateful_context(
            portfolio_id=stateful_input.portfolio_id,
            as_of=stateful_input.as_of,
        ),
        raising=False,
    )

    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_async_stateful_version_base"),
            headers={"Idempotency-Key": "integration-proposal-async-stateful-version-base"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        operation_id, operation_body = _submit_async_version(
            client,
            proposal_id=proposal_id,
            payload={
                "created_by": "advisor_stateful_async",
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "pf_async_stateful_version_base",
                    "as_of": "2026-03-25",
                    "mandate_id": "mandate_async_stateful_version_1",
                },
            },
            correlation_id="corr-integration-proposal-async-stateful-version-1",
        )
        assert operation_body["status"] == "SUCCEEDED"
        version_no = operation_body["result"]["version"]["version_no"]

        proposal_replay = client.get(
            f"/advisory/proposals/{proposal_id}/versions/{version_no}/replay-evidence"
        )
        async_replay = client.get(f"/advisory/proposals/operations/{operation_id}/replay-evidence")
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-version-1"
        )

    assert proposal_replay.status_code == 200
    assert async_replay.status_code == 200
    assert by_correlation.status_code == 200
    proposal_replay_body = proposal_replay.json()
    async_replay_body = async_replay.json()
    assert by_correlation.json()["operation_id"] == operation_id
    assert operation_body["result"]["proposal"]["current_version_no"] == version_no
    assert (
        operation_body["result"]["version"]["proposal_result"]["lineage"]["portfolio_snapshot_id"]
        == "ps_pf_async_stateful_version_base_2026-03-25"
    )
    assert proposal_replay_body["resolved_context"]["portfolio_id"] == (
        "pf_async_stateful_version_base"
    )
    assert proposal_replay_body["evidence"]["context_resolution"]["input_mode"] == "stateful"
    assert (
        proposal_replay_body["hashes"]["request_hash"]
        == async_replay_body["hashes"]["request_hash"]
    )
    assert (
        proposal_replay_body["hashes"]["simulation_hash"]
        == async_replay_body["hashes"]["simulation_hash"]
    )
    assert async_replay_body["continuity"]["async_operation_type"] == "CREATE_PROPOSAL_VERSION"
    assert async_replay_body["continuity"]["correlation_id"] == (
        "corr-integration-proposal-async-stateful-version-1"
    )


def test_stateful_async_create_failure_exposes_terminal_error_and_replay_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(_stateful_input):
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")

    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        _unavailable,
        raising=False,
    )
    payload = {
        "created_by": "advisor_stateful_async",
        "metadata": {
            "title": "Stateful async create failure",
            "advisor_notes": "stateful async failure coverage",
            "jurisdiction": "SG",
        },
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_async_stateful_failure_1",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_async_stateful_failure_1",
        },
    }

    with TestClient(app) as client:
        operation_id, operation_body = _submit_async_create(
            client,
            payload=payload,
            idempotency_key="integration-proposal-async-stateful-failure-1",
            correlation_id="corr-integration-proposal-async-stateful-failure-1",
        )
        async_replay = client.get(f"/advisory/proposals/operations/{operation_id}/replay-evidence")
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-failure-1"
        )

    assert operation_body["status"] == "FAILED"
    assert operation_body["result"] is None
    assert operation_body["error"] == {
        "code": "ProposalValidationError",
        "message": "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE",
    }
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert async_replay.status_code == 200
    replay_body = async_replay.json()
    assert replay_body["subject"]["scope"] == "ASYNC_OPERATION"
    assert replay_body["subject"]["proposal_id"] is None
    assert replay_body["resolved_context"] is None
    assert (
        replay_body["explanation"]["continuity_status"] == "NO_TERMINAL_PROPOSAL_VERSION_AVAILABLE"
    )
    assert replay_body["evidence"]["async_runtime"]["status"] == "FAILED"
    assert replay_body["evidence"]["async_runtime"]["error"] == operation_body["error"]
    assert replay_body["evidence"]["async_runtime"]["finished_at"] is not None


def test_stateful_async_version_failure_exposes_terminal_error_and_replay_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _unavailable(_stateful_input):
        raise LotusCoreContextResolutionError("LOTUS_CORE_STATEFUL_CONTEXT_UNAVAILABLE")

    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        _unavailable,
        raising=False,
    )

    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_async_stateful_failure_base"),
            headers={"Idempotency-Key": "integration-proposal-async-stateful-failure-base"},
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        operation_id, operation_body = _submit_async_version(
            client,
            proposal_id=proposal_id,
            payload={
                "created_by": "advisor_stateful_async",
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "pf_async_stateful_failure_base",
                    "as_of": "2026-03-25",
                    "mandate_id": "mandate_async_stateful_failure_2",
                },
            },
            correlation_id="corr-integration-proposal-async-stateful-failure-version-1",
        )
        async_replay = client.get(f"/advisory/proposals/operations/{operation_id}/replay-evidence")
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-failure-version-1"
        )

    assert operation_body["status"] == "FAILED"
    assert operation_body["proposal_id"] == proposal_id
    assert operation_body["result"] is None
    assert operation_body["error"] == {
        "code": "ProposalValidationError",
        "message": "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE",
    }
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == operation_id
    assert async_replay.status_code == 200
    replay_body = async_replay.json()
    assert replay_body["subject"]["scope"] == "ASYNC_OPERATION"
    assert replay_body["subject"]["proposal_id"] == proposal_id
    assert replay_body["subject"]["proposal_version_no"] is None
    assert replay_body["continuity"]["async_operation_type"] == "CREATE_PROPOSAL_VERSION"
    assert replay_body["evidence"]["async_runtime"]["payload_json"]["proposal_id"] == proposal_id
    assert replay_body["evidence"]["async_runtime"]["error"] == operation_body["error"]
    assert replay_body["explanation"]["source"] == "ASYNC_OPERATION_ONLY"


def test_stateful_async_create_recovers_cleanly_after_initial_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, resolver_state = _flaky_stateful_resolver_factory(
        portfolio_id="pf_async_stateful_recovery_create",
        as_of="2026-03-25",
        use_tradeable_universe=True,
    )
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        resolver,
        raising=False,
    )
    payload = {
        "created_by": "advisor_stateful_async",
        "metadata": {
            "title": "Stateful async create recovery",
            "advisor_notes": "stateful async recovery coverage",
            "jurisdiction": "SG",
        },
        "input_mode": "stateful",
        "stateful_input": {
            "portfolio_id": "pf_async_stateful_recovery_create",
            "as_of": "2026-03-25",
            "mandate_id": "mandate_async_stateful_recovery_create",
        },
    }

    with TestClient(app) as client:
        failed_operation_id, failed_operation = _submit_async_create(
            client,
            payload=payload,
            idempotency_key="integration-proposal-async-stateful-recovery-create-failed",
            correlation_id="corr-integration-proposal-async-stateful-recovery-create-failed",
        )
        recovered_operation_id, recovered_operation = _submit_async_create(
            client,
            payload=payload,
            idempotency_key="integration-proposal-async-stateful-recovery-create-success",
            correlation_id="corr-integration-proposal-async-stateful-recovery-create-success",
        )
        failed_replay = client.get(
            f"/advisory/proposals/operations/{failed_operation_id}/replay-evidence"
        )
        recovered_replay = client.get(
            f"/advisory/proposals/operations/{recovered_operation_id}/replay-evidence"
        )
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-recovery-create-success"
        )

    assert resolver_state["calls"] == 2
    assert failed_operation["status"] == "FAILED"
    assert failed_operation["error"] == {
        "code": "ProposalValidationError",
        "message": "PROPOSAL_STATEFUL_CONTEXT_RESOLUTION_UNAVAILABLE",
    }
    assert recovered_operation["status"] == "SUCCEEDED"
    assert recovered_operation["result"] is not None
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == recovered_operation_id
    assert failed_replay.status_code == 200
    assert recovered_replay.status_code == 200
    failed_replay_body = failed_replay.json()
    recovered_replay_body = recovered_replay.json()
    assert failed_replay_body["subject"]["proposal_id"] is None
    assert failed_replay_body["resolved_context"] is None
    assert (
        recovered_replay_body["subject"]["proposal_id"]
        == recovered_operation["result"]["proposal"]["proposal_id"]
    )
    assert (
        recovered_replay_body["evidence"]["context_resolution"]["resolved_context"][
            "portfolio_snapshot_id"
        ]
        == "ps_pf_async_stateful_recovery_create_2026-03-25"
    )
    assert recovered_replay_body["evidence"]["async_runtime"]["status"] == "SUCCEEDED"


def test_stateful_async_version_recovers_cleanly_after_initial_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, resolver_state = _flaky_stateful_resolver_factory(
        portfolio_id="pf_async_stateful_recovery_version",
        as_of="2026-03-25",
    )
    monkeypatch.setattr(
        "src.api.main.resolve_lotus_core_advisory_context",
        resolver,
        raising=False,
    )

    with TestClient(app) as client:
        created = client.post(
            "/advisory/proposals",
            json=_base_create_payload("pf_async_stateful_recovery_version"),
            headers={
                "Idempotency-Key": "integration-proposal-async-stateful-recovery-version-base"
            },
        )
        assert created.status_code == 200
        proposal_id = created.json()["proposal"]["proposal_id"]

        failed_operation_id, failed_operation = _submit_async_version(
            client,
            proposal_id=proposal_id,
            payload={
                "created_by": "advisor_stateful_async",
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "pf_async_stateful_recovery_version",
                    "as_of": "2026-03-25",
                    "mandate_id": "mandate_async_stateful_recovery_version",
                },
            },
            correlation_id="corr-integration-proposal-async-stateful-recovery-version-failed",
        )
        recovered_operation_id, recovered_operation = _submit_async_version(
            client,
            proposal_id=proposal_id,
            payload={
                "created_by": "advisor_stateful_async",
                "input_mode": "stateful",
                "stateful_input": {
                    "portfolio_id": "pf_async_stateful_recovery_version",
                    "as_of": "2026-03-25",
                    "mandate_id": "mandate_async_stateful_recovery_version",
                },
            },
            correlation_id="corr-integration-proposal-async-stateful-recovery-version-success",
        )
        failed_replay = client.get(
            f"/advisory/proposals/operations/{failed_operation_id}/replay-evidence"
        )
        recovered_replay = client.get(
            f"/advisory/proposals/operations/{recovered_operation_id}/replay-evidence"
        )
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/"
            "corr-integration-proposal-async-stateful-recovery-version-success"
        )
        proposal_version = client.get(
            f"/advisory/proposals/{proposal_id}/versions/"
            f"{recovered_operation['result']['version']['version_no']}"
        )

    assert resolver_state["calls"] == 2
    assert failed_operation["status"] == "FAILED"
    assert failed_operation["proposal_id"] == proposal_id
    assert recovered_operation["status"] == "SUCCEEDED"
    assert recovered_operation["proposal_id"] == proposal_id
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == recovered_operation_id
    assert proposal_version.status_code == 200
    assert failed_replay.status_code == 200
    assert recovered_replay.status_code == 200
    failed_replay_body = failed_replay.json()
    recovered_replay_body = recovered_replay.json()
    assert failed_replay_body["subject"]["proposal_version_no"] is None
    assert failed_replay_body["explanation"]["source"] == "ASYNC_OPERATION_ONLY"
    assert (
        recovered_replay_body["subject"]["proposal_version_no"]
        == recovered_operation["result"]["version"]["version_no"]
    )
    assert recovered_replay_body["resolved_context"]["portfolio_id"] == (
        "pf_async_stateful_recovery_version"
    )
    assert recovered_replay_body["evidence"]["context_resolution"]["input_mode"] == "stateful"


def test_proposal_async_operations_disabled_by_feature_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROPOSAL_ASYNC_OPERATIONS_ENABLED", "false")
    payload = _base_create_payload("pf_integration_proposal_async_disabled")
    with TestClient(app) as client:
        response = client.post(
            "/advisory/proposals/async",
            json=payload,
            headers={"Idempotency-Key": "integration-proposal-async-disabled-1"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATIONS_DISABLED"


def test_async_create_idempotency_reuses_operation_and_blocks_conflicts() -> None:
    payload = _base_create_payload("pf_integration_async_idem_1")
    with TestClient(app) as client:
        first = client.post(
            "/advisory/proposals/async",
            json=payload,
            headers={
                "Idempotency-Key": "integration-proposal-async-idem-1",
                "X-Correlation-Id": "corr-integration-proposal-async-idem-1",
            },
        )
        assert first.status_code == 202
        first_body = first.json()

        duplicate = client.post(
            "/advisory/proposals/async",
            json=payload,
            headers={
                "Idempotency-Key": "integration-proposal-async-idem-1",
                "X-Correlation-Id": "corr-integration-proposal-async-idem-2",
            },
        )
        assert duplicate.status_code == 202
        duplicate_body = duplicate.json()

        conflict_payload = _base_create_payload("pf_integration_async_idem_1")
        conflict_payload["metadata"]["advisor_notes"] = "conflicting async idempotency"
        conflict = client.post(
            "/advisory/proposals/async",
            json=conflict_payload,
            headers={
                "Idempotency-Key": "integration-proposal-async-idem-1",
                "X-Correlation-Id": "corr-integration-proposal-async-idem-3",
            },
        )

        first_operation = client.get(f"/advisory/proposals/operations/{first_body['operation_id']}")
        by_correlation = client.get(
            "/advisory/proposals/operations/by-correlation/corr-integration-proposal-async-idem-1"
        )

    assert duplicate_body["operation_id"] == first_body["operation_id"]
    assert duplicate_body["correlation_id"] == first_body["correlation_id"]
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "IDEMPOTENCY_KEY_CONFLICT: async submission hash mismatch"
    assert first_operation.status_code == 200
    assert by_correlation.status_code == 200
    assert by_correlation.json()["operation_id"] == first_body["operation_id"]


def test_async_create_idempotency_is_stable_under_concurrency() -> None:
    payload = _base_create_payload("pf_integration_async_concurrency_1")
    headers = {"Idempotency-Key": "integration-proposal-async-concurrency-1"}

    def _call() -> tuple[int, str]:
        with TestClient(app) as client:
            response = client.post("/advisory/proposals/async", json=payload, headers=headers)
        body = response.json()
        return response.status_code, body["operation_id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _call(), range(24)))

    statuses = [status for status, _ in results]
    operation_ids = [operation_id for _, operation_id in results]
    assert all(status == 202 for status in statuses)
    assert len(set(operation_ids)) == 1


def test_proposal_async_operation_not_found_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/advisory/proposals/operations/pop_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_ASYNC_OPERATION_NOT_FOUND"


@pytest.mark.parametrize(
    ("env_name", "env_value", "path", "expected_detail"),
    [
        (
            "PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED",
            "false",
            "/advisory/proposals",
            "PROPOSAL_WORKFLOW_LIFECYCLE_DISABLED",
        ),
        (
            "PROPOSAL_SUPPORT_APIS_ENABLED",
            "false",
            "/advisory/proposals/p_missing/approvals",
            "PROPOSAL_SUPPORT_APIS_DISABLED",
        ),
        (
            "PROPOSAL_ASYNC_OPERATIONS_ENABLED",
            "false",
            "/advisory/proposals/operations/pop_missing",
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
        ("/advisory/proposals/p_missing", "PROPOSAL_NOT_FOUND"),
        ("/advisory/proposals/p_missing/versions/1", "PROPOSAL_VERSION_NOT_FOUND"),
        ("/advisory/proposals/p_missing/workflow-events", "PROPOSAL_NOT_FOUND"),
        ("/advisory/proposals/p_missing/approvals", "PROPOSAL_NOT_FOUND"),
        ("/advisory/proposals/p_missing/lineage", "PROPOSAL_NOT_FOUND"),
    ],
)
def test_proposal_not_found_matrix(path: str, expected_detail: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


def test_proposal_idempotency_lookup_not_found_returns_404() -> None:
    with TestClient(app) as client:
        response = client.get("/advisory/proposals/idempotency/idem_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "PROPOSAL_IDEMPOTENCY_KEY_NOT_FOUND"


def test_proposal_simulate_idempotency_is_stable_under_concurrency() -> None:
    payload = {
        "portfolio_snapshot": {
            "portfolio_id": "pf_integration_concurrency_1",
            "base_currency": "USD",
            "positions": [],
            "cash_balances": [{"currency": "USD", "amount": "1000"}],
        },
        "market_data_snapshot": {
            "prices": [{"instrument_id": "EQ_1", "price": "100", "currency": "USD"}],
            "fx_rates": [],
        },
        "shelf_entries": [{"instrument_id": "EQ_1", "status": "APPROVED"}],
        "options": {"enable_proposal_simulation": True},
        "proposed_cash_flows": [],
        "proposed_trades": [{"side": "BUY", "instrument_id": "EQ_1", "quantity": "1"}],
    }
    headers = {"Idempotency-Key": "integration-concurrency-simulate-1"}

    def _call() -> tuple[int, str]:
        with TestClient(app) as client:
            response = client.post("/advisory/proposals/simulate", json=payload, headers=headers)
        body = response.json()
        return response.status_code, body["proposal_run_id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _call(), range(24)))

    statuses = [status for status, _ in results]
    run_ids = [run_id for _, run_id in results]
    assert all(status == 200 for status in statuses)
    assert len(set(run_ids)) == 1


@pytest.mark.parametrize(
    "path",
    [
        "/advisory/proposals/p_missing/workflow-events",
        "/advisory/proposals/p_missing/approvals",
        "/advisory/proposals/p_missing/lineage",
        "/advisory/proposals/idempotency/idem_missing",
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
        "/advisory/proposals",
        "/advisory/proposals/p_missing",
        "/advisory/proposals/p_missing/versions/1",
        "/advisory/proposals/p_missing/workflow-events",
        "/advisory/proposals/p_missing/approvals",
        "/advisory/proposals/p_missing/lineage",
        "/advisory/proposals/operations/pop_missing",
        "/advisory/proposals/operations/by-correlation/corr_missing",
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
        "/advisory/proposals/operations/pop_missing",
        "/advisory/proposals/operations/by-correlation/corr_missing",
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
        ("/advisory/proposals/p_missing/transitions", "PROPOSAL_NOT_FOUND"),
        ("/advisory/proposals/p_missing/approvals", "PROPOSAL_NOT_FOUND"),
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
