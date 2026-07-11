import json
import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Match

from src.api.observability import (
    JsonFormatter,
    _install_instrumentator_route_compatibility,
    _instrumentator_route_name,
    _normalize_request_id,
    correlation_id_var,
    request_id_var,
    routing,
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

    @app.get("/advisory/proposals/{proposal_id}")
    def proposal_route(proposal_id: str) -> dict[str, str]:
        return {"proposal_id": proposal_id}

    @app.get("/advisory/workspaces/{workspace_id}")
    def workspace_route(workspace_id: str) -> dict[str, str]:
        return {"workspace_id": workspace_id}

    @app.get("/advisory/policy-evaluations/{evaluation_id}/lineage")
    def policy_lineage_route(evaluation_id: str) -> dict[str, str]:
        return {"evaluation_id": evaluation_id}

    return app


class _PathlessRouteMarker:
    def matches(self, scope: dict[str, object]) -> tuple[Match, dict[str, object]]:
        return Match.FULL, {}


class _ObservedRoute:
    path = "/observed"

    def matches(self, scope: dict[str, object]) -> tuple[Match, dict[str, object]]:
        return Match.FULL, {}


class _CaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_instrumentator_route_name_skips_pathless_route_markers() -> None:
    assert (
        _instrumentator_route_name(
            {"path": "/observed"},
            [_PathlessRouteMarker(), _ObservedRoute()],
        )
        == "/observed"
    )


def test_route_compatibility_keeps_current_instrumentator_router_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def native_route_name() -> str:
        return "native"

    monkeypatch.setattr(
        "src.api.observability._instrumentator_supports_include_context_routes",
        lambda: True,
    )
    monkeypatch.setattr(routing, "_get_route_name", native_route_name)
    monkeypatch.delattr(routing, "_lotus_advise_pathless_route_compatible", raising=False)

    _install_instrumentator_route_compatibility()

    assert routing._get_route_name is native_route_name
    assert not hasattr(routing, "_lotus_advise_pathless_route_compatible")


def test_route_compatibility_installs_legacy_pathless_route_shim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def legacy_route_name() -> str:
        return "legacy"

    monkeypatch.setattr(
        "src.api.observability._instrumentator_supports_include_context_routes",
        lambda: False,
    )
    monkeypatch.setattr(routing, "_get_route_name", legacy_route_name)
    monkeypatch.delattr(routing, "_lotus_advise_pathless_route_compatible", raising=False)

    _install_instrumentator_route_compatibility()

    assert routing._get_route_name is _instrumentator_route_name
    assert routing._lotus_advise_pathless_route_compatible is True


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


@pytest.mark.parametrize(
    ("path", "route_template", "raw_identifier"),
    [
        (
            "/advisory/proposals/proposal_sg_secret_001",
            "/advisory/proposals/{proposal_id}",
            "proposal_sg_secret_001",
        ),
        (
            "/advisory/workspaces/workspace_secret_001",
            "/advisory/workspaces/{workspace_id}",
            "workspace_secret_001",
        ),
        (
            "/advisory/policy-evaluations/policy_eval_secret_001/lineage",
            "/advisory/policy-evaluations/{evaluation_id}/lineage",
            "policy_eval_secret_001",
        ),
    ],
)
def test_request_completed_logs_use_route_templates_without_raw_identifiers(
    path: str,
    route_template: str,
    raw_identifier: str,
) -> None:
    app = _observed_app()
    capture = _CaptureHandler()
    logger = logging.getLogger("http.access")
    logger.addHandler(capture)

    try:
        with TestClient(app) as client:
            response = client.get(path)
    finally:
        logger.removeHandler(capture)

    assert response.status_code == 200
    fields = _last_http_access_fields(capture.records)
    assert fields["http_method"] == "GET"
    assert fields["endpoint"] == route_template
    assert fields["route_template"] == route_template
    assert fields["operation_name"] == f"GET {route_template}"
    assert fields["http_status_code"] == 200
    assert fields["http_status_class"] == "2xx"
    assert raw_identifier not in json.dumps(fields)


def test_normalize_request_id_trims_meaningful_values() -> None:
    assert _normalize_request_id("  req-observability-trimmed  ") == "req-observability-trimmed"


@pytest.mark.parametrize("request_id", [None, "", "   ", "r" * 129, "req-observability\x7f"])
def test_normalize_request_id_rejects_absent_or_unsafe_values(request_id: str | None) -> None:
    assert _normalize_request_id(request_id) is None


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


def _last_http_access_fields(records: list[logging.LogRecord]) -> dict[str, object]:
    for record in reversed(records):
        if record.name == "http.access" and record.getMessage() == "request.completed":
            fields = getattr(record, "extra_fields", None)
            if isinstance(fields, dict):
                return fields
    raise AssertionError("request.completed log was not emitted")
