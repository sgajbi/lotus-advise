from fastapi.testclient import TestClient

from src.api.main import app


def test_health_endpoints_return_expected_status_payloads():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/health/live").json() == {"status": "live"}
        assert client.get("/health/ready").json() == {"status": "ready"}


def test_versioned_health_endpoints_return_expected_status_payloads():
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert client.get("/api/v1/health/live").json() == {"status": "live"}
        assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
