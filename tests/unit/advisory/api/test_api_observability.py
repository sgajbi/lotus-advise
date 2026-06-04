import json
import logging
import re

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.observability import (
    JsonFormatter,
    correlation_id_var,
    request_id_var,
    setup_observability,
    trace_id_var,
)


def _observed_app() -> FastAPI:
    app = FastAPI()
    setup_observability(app)

    @app.get("/observed")
    def observed() -> dict[str, str]:
        return {
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
            "trace_id": trace_id_var.get(),
        }

    return app


def test_observability_middleware_propagates_correlation_request_and_trace_headers() -> None:
    trace_id = "0123456789abcdef0123456789abcdef"
    traceparent = f"00-{trace_id}-0000000000000001-01"
    with TestClient(_observed_app()) as client:
        response = client.get(
            "/observed",
            headers={
                "X-Correlation-Id": "corr-observability-001",
                "X-Request-Id": "req-observability-001",
                "traceparent": traceparent,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "correlation_id": "corr-observability-001",
        "request_id": "req-observability-001",
        "trace_id": trace_id,
    }
    assert response.headers["X-Correlation-Id"] == "corr-observability-001"
    assert response.headers["X-Request-Id"] == "req-observability-001"
    assert response.headers["X-Trace-Id"] == trace_id
    assert response.headers["traceparent"] == traceparent


def test_observability_middleware_rejects_unsafe_request_id_and_generates_safe_header() -> None:
    with TestClient(_observed_app()) as client:
        response = client.get(
            "/observed",
            headers={
                "X-Correlation-Id": "corr-observability-002",
                "X-Request-Id": "r" * 200,
            },
        )

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "corr-observability-002"
    assert re.fullmatch(r"req_[0-9a-f]{12}", response.json()["request_id"])
    assert response.headers["X-Request-Id"] == response.json()["request_id"]
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["X-Trace-Id"])


def test_json_formatter_includes_context_and_structured_extra_fields() -> None:
    correlation_token = correlation_id_var.set("corr-log")
    request_token = request_id_var.set("req-log")
    trace_token = trace_id_var.set("trace-log")
    try:
        record = logging.LogRecord(
            name="lotus.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="observed",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"endpoint": "/observed", "latency_ms": 12.34}

        payload = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id_var.reset(correlation_token)
        request_id_var.reset(request_token)
        trace_id_var.reset(trace_token)

    assert payload["service"] == "lotus-advise"
    assert payload["correlation_id"] == "corr-log"
    assert payload["request_id"] == "req-log"
    assert payload["trace_id"] == "trace-log"
    assert payload["endpoint"] == "/observed"
    assert payload["latency_ms"] == 12.34
