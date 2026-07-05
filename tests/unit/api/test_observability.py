import json
import logging

import src.api.observability as observability
from src.api.observability import (
    JsonFormatter,
    correlation_id_var,
    record_policy_evaluation_operation,
    request_id_var,
    trace_id_var,
)
from src.api.observability_contracts import (
    POLICY_EVALUATION_OPERATION_FORBIDDEN_LABEL_FIELDS,
    POLICY_EVALUATION_OPERATION_METRIC_LABELS,
)


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


class _FakePolicyOperationCounter:
    def __init__(self):
        self.labels_seen = None
        self.inc_count = 0

    def labels(self, **labels):
        self.labels_seen = labels
        return self

    def inc(self):
        self.inc_count += 1


def test_policy_evaluation_operation_metric_uses_bounded_safe_labels(monkeypatch, caplog):
    fake_counter = _FakePolicyOperationCounter()
    monkeypatch.setattr(observability, "POLICY_EVALUATION_OPERATIONS_TOTAL", fake_counter)

    with caplog.at_level(logging.INFO, logger="policy_evaluation.operations"):
        record_policy_evaluation_operation(
            operation="policy_evaluation.report-package-request",
            status="dependency-unavailable",
            reason="LOTUS_REPORT_REQUEST_UNAVAILABLE",
            dependency="lotus-report",
        )

    assert POLICY_EVALUATION_OPERATION_METRIC_LABELS == (
        "operation",
        "status",
        "reason",
        "dependency",
    )
    assert fake_counter.labels_seen == {
        "operation": "policy_evaluation_report_package_request",
        "status": "dependency_unavailable",
        "reason": "lotus_report_request_unavailable",
        "dependency": "lotus_report",
    }
    assert fake_counter.inc_count == 1
    assert POLICY_EVALUATION_OPERATION_FORBIDDEN_LABEL_FIELDS == (
        "evaluation_id",
        "proposal_id",
        "portfolio_id",
        "actor_id",
        "report_request_id",
        "trace_id",
        "correlation_id",
        "request_id",
        "raw_error",
        "request_path",
        "prompt",
        "source_payload",
        "policy_text",
    )
    assert not set(POLICY_EVALUATION_OPERATION_FORBIDDEN_LABEL_FIELDS).intersection(
        fake_counter.labels_seen
    )
    assert caplog.records[-1].extra_fields == fake_counter.labels_seen
