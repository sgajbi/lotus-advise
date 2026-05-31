from __future__ import annotations

import time
from typing import Any

import httpx

from src.core.bank_demo_proof import (
    BackendRuntimePosture,
    RuntimeEndpointEvidence,
    normalize_runtime_base_url,
)


def probe_runtime_posture(base_url: str, environment: str) -> BackendRuntimePosture:
    normalized_base_url = normalize_runtime_base_url(base_url)
    endpoints: list[RuntimeEndpointEvidence] = []
    with httpx.Client(timeout=10.0) as client:
        endpoints.append(probe_endpoint(client, normalized_base_url, "/health"))
        endpoints.append(probe_endpoint(client, normalized_base_url, "/health/live"))
        endpoints.append(probe_endpoint(client, normalized_base_url, "/health/ready"))
        endpoints.append(probe_endpoint(client, normalized_base_url, "/platform/capabilities"))
    return BackendRuntimePosture(
        base_url=normalized_base_url,
        environment=environment,
        endpoints=endpoints,
    )


def probe_endpoint(
    client: httpx.Client,
    base_url: str,
    endpoint: str,
) -> RuntimeEndpointEvidence:
    started_at = time.perf_counter()
    try:
        response = client.get(f"{base_url.rstrip('/')}{endpoint}")
    except httpx.HTTPError as exc:
        return RuntimeEndpointEvidence(
            endpoint=endpoint,
            http_status=None,
            posture="UNAVAILABLE",
            latency_ms=_elapsed_ms(started_at),
            summary={"error_type": type(exc).__name__},
        )
    summary = (
        _capability_summary(_json_body(response))
        if endpoint == "/platform/capabilities"
        else _health_summary(response)
    )
    posture = "READY" if 200 <= response.status_code < 300 else "DEGRADED"
    return RuntimeEndpointEvidence(
        endpoint=endpoint,
        http_status=response.status_code,
        posture=posture,
        latency_ms=_elapsed_ms(started_at),
        summary=summary,
    )


def not_probed_runtime_posture(base_url: str, environment: str) -> BackendRuntimePosture:
    normalized_base_url = normalize_runtime_base_url(base_url)
    return BackendRuntimePosture(
        base_url=normalized_base_url,
        environment=environment,
        endpoints=[
            RuntimeEndpointEvidence(
                endpoint=endpoint,
                posture="NOT_PROBED",
                summary={"reason": "runtime probe skipped by operator"},
            )
            for endpoint in ("/health", "/health/live", "/health/ready", "/platform/capabilities")
        ],
    )


def _health_summary(response: httpx.Response) -> dict[str, Any]:
    payload = _json_body(response)
    if not isinstance(payload, dict):
        return {"body_type": "non_json"}
    return {key: payload.get(key) for key in ("status", "title", "detail") if key in payload}


def _json_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _elapsed_ms(started_at: float) -> int:
    return int(round((time.perf_counter() - started_at) * 1000))


def _capability_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"body_type": type(payload).__name__}
    readiness = payload.get("readiness") if isinstance(payload.get("readiness"), dict) else {}
    return {
        "feature_keys": [
            item.get("key")
            for item in payload.get("features", [])
            if isinstance(item, dict) and item.get("key")
        ],
        "workflow_keys": [
            item.get("workflow_key")
            for item in payload.get("workflows", [])
            if isinstance(item, dict) and item.get("workflow_key")
        ],
        "operational_ready": readiness.get("operational_ready"),
        "degraded": readiness.get("degraded"),
        "degraded_reasons": readiness.get("degraded_reasons", []),
    }
