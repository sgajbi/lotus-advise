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

    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}
    assert dependencies["lotus_core"]["configured"] is True
    assert dependencies["lotus_core"]["operational_ready"] is True
    assert dependencies["lotus_risk"]["configured"] is True
    assert dependencies["lotus_report"]["configured"] is False
    assert dependencies["lotus_ai"]["configured"] is False
