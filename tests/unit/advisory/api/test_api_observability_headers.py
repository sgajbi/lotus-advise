import re

from fastapi.testclient import TestClient

from src.api.main import app


def test_observability_headers_preserve_inbound_correlation_and_trace_id():
    with TestClient(app) as client:
        response = client.get(
            "/health",
            headers={
                "X-Correlation-Id": "corr-inbound-123",
                "X-Request-Id": "req-inbound-123",
                "traceparent": "00-1234567890abcdef1234567890abcdef-0000000000000001-01",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Correlation-Id"] == "corr-inbound-123"
    assert response.headers["X-Request-Id"] == "req-inbound-123"
    assert response.headers["X-Trace-Id"] == "1234567890abcdef1234567890abcdef"
    assert (
        response.headers["traceparent"] == "00-1234567890abcdef1234567890abcdef-0000000000000001-01"
    )


def test_observability_headers_generate_ids_when_missing():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert re.fullmatch(r"corr_[0-9a-f]{12}", response.headers["X-Correlation-Id"])
    assert re.fullmatch(r"req_[0-9a-f]{12}", response.headers["X-Request-Id"])
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Trace-Id"])
    assert re.fullmatch(
        r"00-[0-9a-f]{32}-0000000000000001-01",
        response.headers["traceparent"],
    )
