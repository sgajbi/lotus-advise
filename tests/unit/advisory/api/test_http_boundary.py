import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.enterprise_readiness import (
    build_enterprise_audit_middleware,
    validate_enterprise_runtime_config,
)
from src.api.http_boundary import approved_security_headers, install_http_boundary
from src.api.main import app as advise_app
from src.api.observability import setup_observability


def test_global_app_adds_security_headers_without_dropping_observability_headers() -> None:
    with TestClient(advise_app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Correlation-Id": "corr-boundary-001",
                "X-Request-Id": "req-boundary-001",
                "traceparent": "00-1234567890abcdef1234567890abcdef-0000000000000001-01",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-boundary-001"
    assert response.headers["X-Request-Id"] == "req-boundary-001"
    assert response.headers["X-Trace-Id"] == "1234567890abcdef1234567890abcdef"
    _assert_security_headers(response)


def test_security_headers_are_added_to_request_validation_errors() -> None:
    with TestClient(_http_boundary_test_app()) as client:
        response = client.get("/items/not-an-int")

    assert response.status_code == 422
    _assert_security_headers(response)


def test_security_headers_are_added_to_payload_limit_denials(monkeypatch) -> None:
    monkeypatch.setenv("ENTERPRISE_MAX_WRITE_PAYLOAD_BYTES", "8")

    with TestClient(_http_boundary_test_app(with_enterprise_audit=True)) as client:
        response = client.post("/write", content=b"012345678")

    assert response.status_code == 413
    assert response.json() == {"detail": "payload_too_large"}
    assert response.headers["X-Enterprise-Policy-Version"] == "1.0.0"
    _assert_security_headers(response)


def test_trusted_host_boundary_allows_configured_host(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_BOUNDARY_TRUSTED_HOSTS", "advise.internal")

    with TestClient(_http_boundary_test_app(), base_url="http://advise.internal") as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_trusted_host_boundary_rejects_unconfigured_host(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_BOUNDARY_TRUSTED_HOSTS", "advise.internal")

    with TestClient(_http_boundary_test_app(), base_url="http://advise.internal") as client:
        response = client.get("/health", headers={"Host": "attacker.invalid"})

    assert response.status_code == 400
    assert "Invalid host header" in response.text


def test_browser_origins_are_denied_by_default() -> None:
    with TestClient(_http_boundary_test_app()) as client:
        response = client.get("/health", headers={"Origin": "https://workbench.lotus.internal"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_configured_browser_origin_receives_cors_headers(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_BOUNDARY_ALLOWED_ORIGINS", "https://workbench.lotus.internal")

    with TestClient(_http_boundary_test_app()) as client:
        response = client.get("/health", headers={"Origin": "https://workbench.lotus.internal"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://workbench.lotus.internal"


def test_configured_browser_origin_allows_scoped_principal_preflight(monkeypatch) -> None:
    monkeypatch.setenv("HTTP_BOUNDARY_ALLOWED_ORIGINS", "https://workbench.lotus.internal")

    with TestClient(_http_boundary_test_app()) as client:
        response = client.options(
            "/write",
            headers={
                "Origin": "https://workbench.lotus.internal",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "X-Principal-Status, X-Authorized-Proposal-Id, X-Authorized-Portfolio-Id"
                ),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://workbench.lotus.internal"


def test_production_like_runtime_requires_explicit_trusted_hosts(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("HTTP_BOUNDARY_TRUSTED_HOSTS", raising=False)
    monkeypatch.setenv("ENTERPRISE_ENFORCE_RUNTIME_CONFIG", "true")

    with pytest.raises(RuntimeError, match="missing_http_trusted_hosts"):
        validate_enterprise_runtime_config()


def test_production_like_runtime_rejects_wildcard_hosts_and_origins(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HTTP_BOUNDARY_TRUSTED_HOSTS", "*.example.com")
    monkeypatch.setenv("HTTP_BOUNDARY_ALLOWED_ORIGINS", "https://*.example.com")

    issues = validate_enterprise_runtime_config()

    assert "wildcard_http_trusted_host" in issues
    assert "wildcard_http_allowed_origin" in issues


def _http_boundary_test_app(*, with_enterprise_audit: bool = False) -> FastAPI:
    app = FastAPI()
    setup_observability(app)
    if with_enterprise_audit:
        app.middleware("http")(build_enterprise_audit_middleware())
    install_http_boundary(app)

    @app.get("/health")
    def _health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/items/{item_id}")
    def _item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    @app.post("/write")
    def _write() -> dict[str, bool]:
        return {"ok": True}

    return app


def _assert_security_headers(response) -> None:
    for header, value in approved_security_headers().items():
        assert response.headers[header] == value
