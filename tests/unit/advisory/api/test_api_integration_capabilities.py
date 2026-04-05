from fastapi.testclient import TestClient

from src.api.main import app


def test_integration_capabilities_response_uses_canonical_snake_case_fields():
    with TestClient(app) as client:
        response = client.get(
            "/platform/capabilities",
            params={"consumer_system": "lotus-gateway", "tenant_id": "default"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert "contract_version" in payload
    assert "source_service" in payload
    assert "consumer_system" in payload
    assert "tenant_id" in payload
    assert "generated_at" in payload
    assert "as_of_date" in payload
    assert "policy_version" in payload
    assert "supported_input_modes" in payload
    assert payload["supported_input_modes"] == ["stateless", "stateful"]

    for legacy_key in (
        "contractVersion",
        "sourceService",
        "consumerSystem",
        "tenantId",
        "generatedAt",
        "asOfDate",
        "policyVersion",
        "supportedInputModes",
    ):
        assert legacy_key not in payload


def test_integration_capabilities_openapi_exposes_snake_case_query_parameters_only():
    openapi = app.openapi()
    operation = openapi["paths"]["/platform/capabilities"]["get"]
    parameter_names = [param["name"] for param in operation["parameters"]]
    assert "consumer_system" in parameter_names
    assert "tenant_id" in parameter_names
    assert "consumerSystem" not in parameter_names
    assert "tenantId" not in parameter_names


def test_integration_capabilities_reports_lotus_dependency_readiness(monkeypatch):
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.delenv("LOTUS_REPORT_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_AI_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_PERFORMANCE_BASE_URL", raising=False)

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["readiness"]["degraded"] is True
    assert payload["readiness"]["operational_ready"] is False
    assert "LOTUS_AI_DEPENDENCY_UNAVAILABLE" in payload["readiness"]["degraded_reasons"]

    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}
    assert dependencies["lotus_core"]["configured"] is True
    assert dependencies["lotus_core"]["operational_ready"] is True
    assert dependencies["lotus_core"]["fallback_mode"] == "NONE"
    assert dependencies["lotus_risk"]["configured"] is True
    assert dependencies["lotus_risk"]["fallback_mode"] == "LOCAL_RISK_FALLBACK"
    assert dependencies["lotus_report"]["configured"] is False
    assert dependencies["lotus_ai"]["configured"] is False

    features = {item["key"]: item for item in payload["features"]}
    assert features["advisory.workspaces.stateful"]["operational_ready"] is True
    assert features["advisory.workspaces.stateful"]["fallback_mode"] == "NONE"
    assert features["advisory.workspaces.ai_rationale"]["operational_ready"] is False
    assert (
        features["advisory.workspaces.ai_rationale"]["degraded_reason"]
        == "LOTUS_AI_DEPENDENCY_UNAVAILABLE"
    )
    assert features["advisory.proposals.reporting"]["operational_ready"] is False
    assert (
        features["advisory.proposals.reporting"]["degraded_reason"]
        == "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"
    )
    assert features["advisory.proposals.execution_handoff"]["operational_ready"] is True

    workflows = {item["workflow_key"]: item for item in payload["workflows"]}
    assert workflows["advisory_workspace_stateful"]["operational_ready"] is True
    assert workflows["advisory_workspace_ai_rationale"]["operational_ready"] is False
    assert workflows["advisory_proposal_reporting"]["operational_ready"] is False
    assert workflows["advisory_proposal_execution_handoff"]["operational_ready"] is True


def test_integration_capabilities_disable_reporting_and_execution_with_lifecycle(monkeypatch):
    monkeypatch.setenv("PROPOSAL_WORKFLOW_LIFECYCLE_ENABLED", "false")
    monkeypatch.setenv("LOTUS_REPORT_BASE_URL", "http://lotus-report:8300")

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}
    assert features["advisory.proposals.reporting"]["enabled"] is False
    assert features["advisory.proposals.reporting"]["operational_ready"] is False
    assert features["advisory.proposals.execution_handoff"]["enabled"] is False
    assert workflows["advisory_proposal_reporting"]["enabled"] is False
    assert workflows["advisory_proposal_execution_handoff"]["enabled"] is False
