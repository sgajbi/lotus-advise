from fastapi.testclient import TestClient

import src.api.main as main_module
from src.api.main import app
from src.api.problem_details import build_problem_detail_response


def test_health_endpoints_return_expected_status_payloads():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/health/live").json() == {"status": "live"}
        assert client.get("/health/ready").json() == {"status": "ready"}


def test_version_endpoint_exposes_support_safe_build_metadata(monkeypatch):
    monkeypatch.setenv("LOTUS_BUILD_COMMIT_SHA", "abc123")
    monkeypatch.setenv("LOTUS_BUILD_GIT_BRANCH", "feat/provenance")
    monkeypatch.setenv("LOTUS_BUILD_REPO_URL", "https://github.com/sgajbi/lotus-advise")
    monkeypatch.setenv("LOTUS_BUILD_VERSION", "0.1.0")
    monkeypatch.setenv("LOTUS_BUILD_TIMESTAMP", "2026-07-11T00:00:00Z")
    monkeypatch.setenv("LOTUS_CI_PIPELINE_ID", "123456")
    monkeypatch.setenv("LOTUS_IMAGE_DIGEST", "sha256:abc")

    with TestClient(app) as client:
        payload = client.get("/version").json()

    assert payload == {
        "service_name": "lotus-advise",
        "service_version": "0.1.0",
        "git_commit_sha": "abc123",
        "git_branch": "feat/provenance",
        "repository_url": "https://github.com/sgajbi/lotus-advise",
        "build_timestamp_utc": "2026-07-11T00:00:00Z",
        "ci_pipeline_run_id": "123456",
        "image_digest": "sha256:abc",
    }


def test_no_versioned_health_endpoints_are_exposed():
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 404
        assert client.get("/api/v1/health/live").status_code == 404
        assert client.get("/api/v1/health/ready").status_code == 404


def test_health_ready_returns_503_when_runtime_probe_fails(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_readiness_probe",
        lambda: (False, "PROPOSAL_POSTGRES_CONNECTION_FAILED"),
    )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"] == "PROPOSAL_POSTGRES_CONNECTION_FAILED"


def test_health_ready_stays_local_when_dependency_capabilities_are_degraded(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("LOTUS_CORE_BASE_URL", raising=False)
    monkeypatch.setenv("LOTUS_RISK_BASE_URL", "http://lotus-risk:8130")
    monkeypatch.setenv("LOTUS_REPORT_BASE_URL", "http://lotus-report:8300")
    monkeypatch.delenv("LOTUS_AI_BASE_URL", raising=False)
    monkeypatch.delenv("LOTUS_PERFORMANCE_BASE_URL", raising=False)
    monkeypatch.setattr(
        main_module, "validate_configured_integration_runtime_settings", lambda: None
    )
    monkeypatch.setattr(main_module, "validate_advisory_runtime_persistence", lambda: None)
    monkeypatch.setattr(main_module, "ensure_proposal_runtime_ready", lambda: None)
    monkeypatch.setattr(
        "src.integrations.base.probe_dependency_health",
        lambda base_url: "lotus-risk" not in base_url and "lotus-report" not in base_url,
    )

    with TestClient(app) as client:
        ready_response = client.get("/health/ready")
        capabilities_response = client.get("/platform/capabilities")

    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ready"}
    assert capabilities_response.status_code == 200
    capabilities_payload = capabilities_response.json()
    assert capabilities_payload["readiness"]["operational_ready"] is False
    dependencies = {
        item["dependency_key"]: item for item in capabilities_payload["readiness"]["dependencies"]
    }
    assert dependencies["lotus_core"]["readiness_basis"] == "not_configured"
    assert dependencies["lotus_core"]["degraded_reason"] == "LOTUS_CORE_DEPENDENCY_UNAVAILABLE"
    assert dependencies["lotus_risk"]["readiness_basis"] == "probe_failed"
    assert dependencies["lotus_risk"]["degraded_reason"] == "LOTUS_RISK_DEPENDENCY_UNAVAILABLE"
    assert dependencies["lotus_report"]["readiness_basis"] == "probe_failed"
    assert dependencies["lotus_report"]["degraded_reason"] == "LOTUS_REPORT_DEPENDENCY_UNAVAILABLE"


def test_readiness_probe_redacts_sensitive_runtime_failure(monkeypatch):
    def _raise_sensitive_runtime_error() -> None:
        raise RuntimeError("postgres password secret leaked from driver")

    monkeypatch.setattr(
        main_module,
        "validate_advisory_runtime_persistence",
        _raise_sensitive_runtime_error,
    )

    ready, detail = main_module._readiness_probe()

    assert ready is False
    assert detail == "READINESS_CHECK_FAILED"


def test_problem_detail_response_builder_preserves_standard_shape():
    response = build_problem_detail_response(
        status_code=503,
        title="Service Unavailable",
        detail="READINESS_CHECK_FAILED",
        instance="/health/ready",
        correlation_id="corr-health-001",
    )

    assert response.status_code == 503
    assert response.media_type == "application/problem+json"
    assert response.body == (
        b'{"type":"about:blank","title":"Service Unavailable","status":503,'
        b'"detail":"READINESS_CHECK_FAILED","instance":"/health/ready",'
        b'"correlation_id":"corr-health-001"}'
    )
