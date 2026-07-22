import pytest

import scripts.run_demo_pack_live as demo_pack
from scripts.run_demo_pack_live import (
    REQUIRED_FEATURE_KEYS,
    REQUIRED_WORKFLOW_KEYS,
    DemoRunError,
    _assert_capability_truth,
    _openapi_operations,
    _route_safety_probe,
    _sample_path,
)
from src.api.capabilities.service import build_integration_capabilities


def test_openapi_operations_inventory_counts_declared_http_methods() -> None:
    schema = {
        "paths": {
            "/health": {"get": {"operationId": "health", "tags": ["Health"]}},
            "/advisory/proposals": {
                "post": {
                    "operationId": "createProposal",
                    "tags": ["Advisory Proposal Lifecycle"],
                    "requestBody": {"required": True},
                }
            },
        }
    }

    assert _openapi_operations(schema) == [
        {
            "method": "POST",
            "path": "/advisory/proposals",
            "operationId": "createProposal",
            "tags": ["Advisory Proposal Lifecycle"],
            "requiresRequestBody": True,
        },
        {
            "method": "GET",
            "path": "/health",
            "operationId": "health",
            "tags": ["Health"],
            "requiresRequestBody": False,
        },
    ]


def test_sample_path_uses_deterministic_demo_parameters() -> None:
    assert (
        _sample_path("/advisory/proposals/{proposal_id}/versions/{version_no}/memo")
        == "/advisory/proposals/demo-proposal-id/versions/1/memo"
    )


def test_lifecycle_demo_scenarios_send_idempotency_keys(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_scenario(_client, **kwargs):
        calls.append(kwargs)
        name = kwargs["name"]
        if name == "20_advisory_proposal_persist_create.json":
            return {"proposal": {"proposal_id": "proposal-demo", "current_state": "DRAFT"}}
        if name == "21_advisory_proposal_new_version.json":
            return {"proposal": {"current_version_no": 2}}
        if name == "22_advisory_proposal_transition_to_compliance.json":
            return {"current_state": "COMPLIANCE_REVIEW"}
        if name == "24_advisory_proposal_approval_compliance.json":
            return {"current_state": "AWAITING_CLIENT_CONSENT"}
        if name == "23_advisory_proposal_approval_client_consent.json":
            return {"current_state": "EXECUTION_READY"}
        if name == "25_advisory_proposal_transition_executed.json":
            return {"current_state": "EXECUTED"}
        if name == "list_proposals":
            return {"items": [{"proposal_id": "proposal-demo"}]}
        raise AssertionError(f"unexpected scenario {name}")

    monkeypatch.setattr(demo_pack, "_run_scenario", fake_run_scenario)
    evidence = {"scenarios": [], "domainAssertions": []}

    demo_pack._certify_lifecycle_scenarios(object(), evidence)

    post_calls_after_create = [
        call
        for call in calls
        if call["method"] == "POST" and call["name"] != "20_advisory_proposal_persist_create.json"
    ]
    assert post_calls_after_create
    for call in post_calls_after_create:
        headers = call.get("headers")
        assert isinstance(headers, dict)
        assert str(headers["Idempotency-Key"]).startswith("live-demo-lifecycle-")


def test_capability_truth_accepts_required_ready_features_and_workflows() -> None:
    capabilities = {
        "features": [
            {"key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_FEATURE_KEYS)
        ],
        "workflows": [
            {"workflow_key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_WORKFLOW_KEYS)
        ],
        "supportability": {"state": "ready"},
        "readiness": {"operational_ready": True},
    }

    evidence = _assert_capability_truth(capabilities)

    assert evidence["requiredFeatureCount"] > 0
    assert evidence["requiredWorkflowCount"] > 0
    assert evidence["supportability"]["state"] == "ready"


def test_capability_truth_preserves_truthful_dependency_degraded_posture() -> None:
    capabilities = {
        "features": [
            {"key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_FEATURE_KEYS)
        ],
        "workflows": [
            {"workflow_key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_WORKFLOW_KEYS)
        ],
        "supportability": {"state": "degraded"},
        "readiness": {"operational_ready": False},
    }
    capabilities["features"][0] = {
        "key": sorted(REQUIRED_FEATURE_KEYS)[0],
        "enabled": True,
        "operational_ready": False,
        "dependency_keys": ["lotus_report"],
        "degraded_reason": "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE",
    }
    capabilities["workflows"][0] = {
        "workflow_key": sorted(REQUIRED_WORKFLOW_KEYS)[0],
        "enabled": True,
        "operational_ready": False,
        "dependency_keys": ["lotus_ai"],
        "degraded_reason": "LOTUS_AI_DEPENDENCY_UNAVAILABLE",
    }

    evidence = _assert_capability_truth(capabilities)

    assert evidence["degradedRequiredFeatures"] == [capabilities["features"][0]["key"]]
    assert evidence["degradedRequiredWorkflows"] == [capabilities["workflows"][0]["workflow_key"]]


def test_capability_truth_accepts_real_dependency_degraded_capability_payload(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.delenv("LOTUS_REPORT_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_AI_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_PERFORMANCE_BASE_URL", raising=False)

    capabilities = build_integration_capabilities(consumer_system="lotus-gateway").model_dump(
        mode="json"
    )

    evidence = _assert_capability_truth(capabilities)

    assert set(evidence["degradedRequiredFeatures"]) == {
        "advisory.advisory_copilot",
        "advisory.bank_demo_proof",
        "advisory.proposals.memo_evidence_pack",
        "advisory.proposals.policy_evaluation",
        "advisory.proposals.reporting",
    }
    assert set(evidence["degradedRequiredWorkflows"]) == {
        "advisory_bank_demo_proof",
        "advisory_copilot_interaction",
        "advisory_policy_evaluation",
        "advisory_proposal_memo_evidence_pack",
        "advisory_proposal_reporting",
    }


def test_capability_truth_rejects_unexplained_unready_required_feature() -> None:
    capabilities = {
        "features": [
            {"key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_FEATURE_KEYS)
        ],
        "workflows": [
            {"workflow_key": key, "enabled": True, "operational_ready": True}
            for key in sorted(REQUIRED_WORKFLOW_KEYS)
        ],
    }
    capabilities["features"][0]["operational_ready"] = False

    with pytest.raises(DemoRunError, match="Required capability features are not ready"):
        _assert_capability_truth(capabilities)


def test_capability_truth_rejects_missing_required_feature() -> None:
    capabilities = {
        "features": [],
        "workflows": [],
    }

    with pytest.raises(DemoRunError, match="Missing required capability features"):
        _assert_capability_truth(capabilities)


def test_route_safety_probe_skips_no_body_post_even_with_path_parameters() -> None:
    class FailingClient:
        def request(self, *_args, **_kwargs):
            raise AssertionError("no-body POST probe must not call the live route")

    record = _route_safety_probe(
        FailingClient(),
        {
            "method": "POST",
            "path": "/advisory/workspaces/{workspace_id}/evaluate",
            "operationId": "evaluateWorkspace",
            "requiresRequestBody": False,
        },
    )

    assert record["status"] == "skipped"
    assert record["reason"] == "mutating_no_required_body_operation_not_probed"


def test_run_demo_pack_writes_failure_evidence(tmp_path, monkeypatch) -> None:
    def fail_foundation(_client, _evidence):
        raise DemoRunError("boom")

    output = tmp_path / "demo-certification.json"
    monkeypatch.setattr(demo_pack, "_certify_foundation", fail_foundation)

    with pytest.raises(DemoRunError, match="boom"):
        demo_pack.run_demo_pack("http://127.0.0.1:8000", output=output)

    evidence = demo_pack.json.loads(output.read_text(encoding="utf-8"))
    assert evidence["status"] == "failed"
    assert evidence["error"] == {"type": "DemoRunError", "message": "boom"}
