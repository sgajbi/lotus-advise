import json
import logging

from src.api.observability import JsonFormatter, correlation_id_var, request_id_var, trace_id_var


def test_json_formatter_includes_context_extra_and_audit_fields(monkeypatch):
    monkeypatch.setenv("SERVICE_NAME", "lotus-advise-test")
    monkeypatch.setenv("ENVIRONMENT", "test")
    correlation_token = correlation_id_var.set("corr-001")
    request_token = request_id_var.set("req-001")
    trace_token = trace_id_var.set("trace-001")

    try:
        record = logging.LogRecord(
            name="lotus.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="request.completed",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"endpoint": "/health/ready", "latency_ms": 12.5}
        record.audit = {"event": "ready_check"}

        payload = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id_var.reset(correlation_token)
        request_id_var.reset(request_token)
        trace_id_var.reset(trace_token)

    assert payload["service"] == "lotus-advise-test"
    assert payload["environment"] == "test"
    assert payload["logger"] == "lotus.test"
    assert payload["message"] == "request.completed"
    assert payload["correlation_id"] == "corr-001"
    assert payload["request_id"] == "req-001"
    assert payload["trace_id"] == "trace-001"
    assert payload["endpoint"] == "/health/ready"
    assert payload["latency_ms"] == 12.5
    assert payload["audit"] == {"event": "ready_check"}
    assert "timestamp" in payload


def test_json_formatter_omits_absent_context_and_ignores_malformed_extra_fields():
    record = logging.LogRecord(
        name="lotus.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="request.warning",
        args=(),
        exc_info=None,
    )
    record.extra_fields = ["not", "a", "mapping"]
    record.audit = "not-a-mapping"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "WARNING"
    assert payload["message"] == "request.warning"
    assert "correlation_id" not in payload
    assert "request_id" not in payload
    assert "trace_id" not in payload
    assert "audit" not in payload
