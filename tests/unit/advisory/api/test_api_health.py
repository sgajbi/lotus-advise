from fastapi.testclient import TestClient

import src.api.main as main_module
from src.api.main import app


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
