import json
import logging
import os
import time
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from packaging.version import InvalidVersion, Version
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator, routing
from starlette.routing import Match, Mount

from src.api.observability_contracts import ADVISORY_SUPPORTABILITY_METRIC_LABELS
from src.core.proposals.correlation import (
    normalize_optional_correlation_id,
    resolve_correlation_id,
)

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

ADVISORY_SUPPORTABILITY_TOTAL = Counter(
    "lotus_advise_advisory_supportability_total",
    "Count of advisory supportability posture evaluations.",
    ADVISORY_SUPPORTABILITY_METRIC_LABELS,
)

_INSTRUMENTATOR_INCLUDE_CONTEXT_ROUTE_VERSION = Version("8.0.1")


@dataclass(frozen=True)
class _RouteNameResolution:
    route_name: str | None
    complete: bool


def _meaningful_header(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_request_id(request_id: str | None) -> str | None:
    normalized: str | None = normalize_optional_correlation_id(request_id)
    return normalized


def _resolve_request_id(request_id: str | None) -> str:
    meaningful_request_id = _normalize_request_id(request_id)
    return meaningful_request_id or f"req_{uuid4().hex[:12]}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = _log_payload(record)
        return json.dumps(_without_none_values(payload))


def _log_payload(record: logging.LogRecord) -> dict[str, object]:
    payload = _base_log_payload(record)
    payload.update(_extra_log_fields(record))
    audit = _audit_log_fields(record)
    if audit is not None:
        payload["audit"] = audit
    return payload


def _base_log_payload(record: logging.LogRecord) -> dict[str, object]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": record.levelname,
        "service": os.getenv("SERVICE_NAME", "lotus-advise"),
        "environment": os.getenv("ENVIRONMENT", "local"),
        "logger": record.name,
        "message": record.getMessage(),
        "correlation_id": correlation_id_var.get() or None,
        "request_id": request_id_var.get() or None,
        "trace_id": trace_id_var.get() or None,
    }


def _extra_log_fields(record: logging.LogRecord) -> dict[str, object]:
    extra_fields = getattr(record, "extra_fields", None)
    if isinstance(extra_fields, dict):
        return extra_fields
    return {}


def _audit_log_fields(record: logging.LogRecord) -> dict[str, object] | None:
    audit = getattr(record, "audit", None)
    if isinstance(audit, dict):
        return audit
    return None


def _without_none_values(payload: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if value is not None}


def setup_observability(app: FastAPI) -> None:
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    _install_instrumentator_route_compatibility()
    Instrumentator().instrument(app).expose(app)

    @app.middleware("http")
    async def _request_observability_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        logger = logging.getLogger("http.access")
        started = time.perf_counter()

        correlation_id = resolve_correlation_id(request.headers.get("X-Correlation-Id"))
        request_id = _resolve_request_id(request.headers.get("X-Request-Id"))
        traceparent = _meaningful_header(request.headers.get("traceparent")) or ""
        trace_id = uuid4().hex
        if traceparent:
            parts = traceparent.split("-")
            if len(parts) >= 4 and len(parts[1]) == 32:
                trace_id = parts[1]

        correlation_token = correlation_id_var.set(correlation_id)
        request_token = request_id_var.set(request_id)
        trace_token = trace_id_var.set(trace_id)
        try:
            response: Response = await call_next(request)
        finally:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "extra_fields": {
                        "http_method": request.method,
                        "endpoint": request.url.path,
                        "latency_ms": latency_ms,
                    }
                },
            )
            correlation_id_var.reset(correlation_token)
            request_id_var.reset(request_token)
            trace_id_var.reset(trace_token)

        response_correlation_id = (
            normalize_optional_correlation_id(response.headers.get("X-Correlation-Id"))
            or correlation_id
        )
        response.headers["X-Correlation-Id"] = response_correlation_id
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["traceparent"] = f"00-{trace_id}-0000000000000001-01"
        return response


def record_advisory_supportability(
    *,
    state: str,
    reason: str,
    freshness_bucket: str,
) -> None:
    ADVISORY_SUPPORTABILITY_TOTAL.labels(
        state=state,
        reason=reason,
        freshness_bucket=freshness_bucket,
    ).inc()


def _install_instrumentator_route_compatibility() -> None:
    if _instrumentator_supports_include_context_routes():
        return
    if getattr(routing, "_lotus_advise_pathless_route_compatible", False):
        return
    routing._get_route_name = _instrumentator_route_name  # type: ignore[attr-defined]
    routing._lotus_advise_pathless_route_compatible = True


def _instrumentator_supports_include_context_routes() -> bool:
    try:
        installed_version = Version(version("prometheus-fastapi-instrumentator"))
    except (PackageNotFoundError, InvalidVersion):
        return False
    return installed_version >= _INSTRUMENTATOR_INCLUDE_CONTEXT_ROUTE_VERSION


def _instrumentator_route_name(
    scope: dict[str, object],
    routes: list[object],
    route_name: str | None = None,
) -> str | None:
    candidate_route_name = route_name
    for route in routes:
        resolution = _route_name_resolution(scope, route, candidate_route_name)
        if resolution is None:
            continue
        candidate_route_name = resolution.route_name
        if resolution.complete:
            return candidate_route_name
    return candidate_route_name


def _route_name_resolution(
    scope: dict[str, object],
    route: object,
    route_name: str | None,
) -> _RouteNameResolution | None:
    match_result = _match_route(route, scope)
    if match_result is None:
        return None
    match, child_scope = match_result
    path = _route_path(route)
    if path is None:
        return _pathless_route_name_resolution(
            route=route,
            match=match,
            scope=scope,
            child_scope=child_scope,
            route_name=route_name,
        )
    return _path_route_name_resolution(
        route=route,
        match=match,
        path=path,
        scope=scope,
        child_scope=child_scope,
        route_name=route_name,
    )


def _path_route_name_resolution(
    *,
    route: object,
    match: Match,
    path: str,
    scope: dict[str, object],
    child_scope: dict[str, object],
    route_name: str | None,
) -> _RouteNameResolution | None:
    if match == Match.FULL:
        return _RouteNameResolution(
            _full_route_name(
                route=route,
                path=path,
                scope=scope,
                child_scope=child_scope,
            ),
            complete=True,
        )
    if match == Match.PARTIAL and route_name is None:
        return _RouteNameResolution(path, complete=False)
    return None


def _match_route(
    route: object,
    scope: dict[str, object],
) -> tuple[Match, dict[str, object]] | None:
    matches = getattr(route, "matches", None)
    if not callable(matches):
        return None
    match, child_scope = matches(scope)
    return match, child_scope


def _route_path(route: object) -> str | None:
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else None


def _pathless_route_name_resolution(
    *,
    route: object,
    match: Match,
    scope: dict[str, object],
    child_scope: dict[str, object],
    route_name: str | None,
) -> _RouteNameResolution | None:
    nested_routes = getattr(route, "routes", None)
    if match != Match.FULL or not isinstance(nested_routes, list):
        return None
    nested_route_name = _instrumentator_route_name(
        {**scope, **child_scope},
        nested_routes,
        route_name,
    )
    if nested_route_name is None:
        return None
    return _RouteNameResolution(nested_route_name, complete=True)


def _full_route_name(
    *,
    route: object,
    path: str,
    scope: dict[str, object],
    child_scope: dict[str, object],
) -> str | None:
    if not isinstance(route, Mount) or not route.routes:
        return path
    child_route_name = _instrumentator_route_name(
        {**scope, **child_scope},
        route.routes,
        path,
    )
    return None if child_route_name is None else path + child_route_name
