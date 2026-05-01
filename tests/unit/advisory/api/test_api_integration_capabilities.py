from fastapi.testclient import TestClient

from src.api.main import app
from src.api.observability_contracts import ADVISORY_SUPPORTABILITY_METRIC_LABELS

_FORBIDDEN_SUPPORTABILITY_METRIC_LABELS = (
    "portfolio_id",
    "account_id",
    "client_id",
    "advisor_id",
    "proposal_id",
    "workspace_id",
    "correlation_id",
    "trace_id",
    "request_id",
    "transaction_id",
    "security_id",
    "request_body",
    "response_body",
)


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
    assert features["advisory.proposals.simulation"]["operational_ready"] is True
    assert features["advisory.proposals.simulation"]["owner_service"] == "LOTUS_CORE"
    assert features["advisory.proposals.simulation"]["fallback_mode"] == "NONE"
    assert features["advisory.proposals.risk_lens"]["operational_ready"] is True
    assert features["advisory.proposals.risk_lens"]["owner_service"] == "LOTUS_RISK"
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
    assert features["advise.observability.advisory_supportability"]["enabled"] is True
    assert features["advise.observability.advisory_supportability"]["owner_service"] == "ADVISORY"

    workflows = {item["workflow_key"]: item for item in payload["workflows"]}
    assert workflows["advisory_proposal_simulation"]["operational_ready"] is True
    assert workflows["advisory_proposal_risk_lens"]["operational_ready"] is True
    assert workflows["advisory_workspace_stateful"]["operational_ready"] is True
    assert workflows["advisory_workspace_ai_rationale"]["operational_ready"] is False
    assert workflows["advisory_proposal_reporting"]["operational_ready"] is False
    assert workflows["advisory_proposal_execution_handoff"]["operational_ready"] is True
    assert payload["supportability"] == {
        "state": "degraded",
        "reason": "dependency_degraded",
        "freshness_bucket": "unknown",
        "metric_labels": list(ADVISORY_SUPPORTABILITY_METRIC_LABELS),
        "dependency_count": 5,
        "ready_dependency_count": 2,
        "degraded_dependency_count": 3,
        "enabled_feature_count": 9,
        "ready_feature_count": 7,
    }


def test_integration_capabilities_mark_risk_lens_degraded_when_risk_missing(monkeypatch):
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.delenv("LOTUS_RISK_BASE_URL", raising=False)

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}

    assert features["advisory.proposals.risk_lens"]["operational_ready"] is False
    assert (
        features["advisory.proposals.risk_lens"]["degraded_reason"]
        == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    )
    assert workflows["advisory_proposal_risk_lens"]["operational_ready"] is False
    assert (
        workflows["advisory_proposal_risk_lens"]["degraded_reason"]
        == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    )


def test_integration_capabilities_mark_risk_lens_degraded_when_production_probe_fails(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.base.probe_dependency_health",
        lambda base_url: "lotus-risk" not in base_url,
    )

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}

    assert dependencies["lotus_risk"]["operational_ready"] is False
    assert features["advisory.proposals.risk_lens"]["operational_ready"] is False
    assert (
        features["advisory.proposals.risk_lens"]["degraded_reason"]
        == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    )
    assert workflows["advisory_proposal_risk_lens"]["operational_ready"] is False
    assert (
        workflows["advisory_proposal_risk_lens"]["degraded_reason"]
        == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    )


def test_integration_capabilities_mark_simulation_degraded_when_core_missing(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}
    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}

    assert features["advisory.proposals.simulation"]["operational_ready"] is False
    assert (
        features["advisory.proposals.simulation"]["fallback_mode"]
        == "CONTROLLED_LOCAL_SIMULATION_FALLBACK"
    )
    assert (
        features["advisory.proposals.simulation"]["degraded_reason"]
        == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    )
    assert workflows["advisory_proposal_simulation"]["operational_ready"] is False
    assert dependencies["lotus_core"]["fallback_mode"] == "CONTROLLED_LOCAL_SIMULATION_FALLBACK"


def test_integration_capabilities_mark_core_unready_when_production_probe_fails(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setattr(
        "src.integrations.base.probe_dependency_health",
        lambda base_url: "lotus-core" not in base_url,
    )

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}

    assert dependencies["lotus_core"]["operational_ready"] is False
    assert dependencies["lotus_core"]["fallback_mode"] == "NONE"
    assert features["advisory.proposals.simulation"]["operational_ready"] is False
    assert features["advisory.proposals.simulation"]["fallback_mode"] == "NONE"
    assert (
        features["advisory.proposals.simulation"]["degraded_reason"]
        == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    )
    assert workflows["advisory_proposal_simulation"]["operational_ready"] is False
    assert (
        workflows["advisory_proposal_simulation"]["degraded_reason"]
        == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    )


def test_integration_capabilities_quarantine_local_fallback_in_production(monkeypatch):
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_ADVISE_ALLOW_LOCAL_SIMULATION_FALLBACK", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    features = {item["key"]: item for item in payload["features"]}
    workflows = {item["workflow_key"]: item for item in payload["workflows"]}
    dependencies = {item["dependency_key"]: item for item in payload["readiness"]["dependencies"]}

    assert features["advisory.proposals.simulation"]["operational_ready"] is False
    assert features["advisory.proposals.simulation"]["fallback_mode"] == "NONE"
    assert workflows["advisory_proposal_simulation"]["operational_ready"] is False
    assert dependencies["lotus_core"]["fallback_mode"] == "NONE"


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
    assert features["advise.observability.advisory_supportability"]["operational_ready"] is False
    assert payload["supportability"]["state"] == "unsupported"
    assert payload["supportability"]["reason"] == "lifecycle_disabled"


def test_integration_capabilities_reports_ready_advisory_supportability(monkeypatch):
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setenv("LOTUS_REPORT_BASE_URL", "http://lotus-report:8300")
    monkeypatch.setenv("LOTUS_AI_BASE_URL", "http://lotus-ai:8400")
    monkeypatch.setenv("LOTUS_PERFORMANCE_BASE_URL", "http://lotus-performance:8301")

    with TestClient(app) as client:
        response = client.get("/platform/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supportability"] == {
        "state": "ready",
        "reason": "advisory_ready",
        "freshness_bucket": "current",
        "metric_labels": list(ADVISORY_SUPPORTABILITY_METRIC_LABELS),
        "dependency_count": 5,
        "ready_dependency_count": 5,
        "degraded_dependency_count": 0,
        "enabled_feature_count": 9,
        "ready_feature_count": 9,
    }


def test_integration_capabilities_records_bounded_supportability_metric(monkeypatch):
    monkeypatch.setenv("LOTUS_CORE_BASE_URL", "http://lotus-core:8201")
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setenv("LOTUS_REPORT_BASE_URL", "http://lotus-report:8300")
    monkeypatch.setenv("LOTUS_AI_BASE_URL", "http://lotus-ai:8400")
    monkeypatch.setenv("LOTUS_PERFORMANCE_BASE_URL", "http://lotus-performance:8301")

    with TestClient(app) as client:
        capabilities_response = client.get("/platform/capabilities")
        metrics_response = client.get("/metrics")

    assert capabilities_response.status_code == 200
    assert metrics_response.status_code == 200
    metrics_text = metrics_response.text
    assert "lotus_advise_advisory_supportability_total" in metrics_text
    assert 'freshness_bucket="current"' in metrics_text
    assert 'reason="advisory_ready"' in metrics_text
    assert 'state="ready"' in metrics_text
    for forbidden_label in _FORBIDDEN_SUPPORTABILITY_METRIC_LABELS:
        assert f"{forbidden_label}=" not in metrics_text


def test_integration_capabilities_openapi_documents_supportability_metric_labels():
    openapi = app.openapi()
    supportability_schema = openapi["components"]["schemas"]["AdvisorySupportability"]
    metric_labels = supportability_schema["properties"]["metric_labels"]

    assert metric_labels["default"] == list(ADVISORY_SUPPORTABILITY_METRIC_LABELS)
    assert "lotus_advise_advisory_supportability_total" in metric_labels["description"]
    assert "portfolio" in metric_labels["description"]
    assert "trace" in metric_labels["description"]
