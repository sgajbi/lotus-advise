from fastapi.testclient import TestClient

import src.api.main as main_module
from src.api.main import app
from src.api.problem_details import build_problem_detail_response


def test_health_endpoints_return_expected_status_payloads():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/health/live").json() == {"status": "live"}
        assert client.get("/health/ready").json() == {"status": "ready"}


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
