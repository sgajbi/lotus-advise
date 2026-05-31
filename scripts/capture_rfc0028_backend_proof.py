from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.live_runtime_suite_artifacts import (  # noqa: E402
    load_result_json,
    resolve_bundle_dir,
    result_to_json_dict,
    write_live_runtime_suite_bundle,
)
from scripts.rfc0028_backend_proof_writer import (  # noqa: E402
    write_backend_proof_capture_bundle,
)
from scripts.validate_live_runtime_suite import validate_live_runtime_suite  # noqa: E402
from src.core.bank_demo_proof import (  # noqa: E402
    BackendRuntimePosture,
    RuntimeEndpointEvidence,
    build_backend_proof_capture,
    default_capture_metadata,
    normalize_output_ref_prefix,
    normalize_runtime_base_url,
)

_DEFAULT_ADVISE_BASE_URL = "http://advise.dev.lotus"
_DEFAULT_SERVICE_VERSION = "0.1.0"
_DEFAULT_OUTPUT_DIR = "output/rfc0028/backend-proof"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Capture an RFC-0028 backend proof pack from the governed live runtime suite. "
            "Artifacts are sanitized and intended for ignored output/ evidence directories."
        )
    )
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument(
        "--live-suite-json",
        default=None,
        help="Path to an existing live runtime suite result.json artifact.",
    )
    source_group.add_argument(
        "--live-suite-bundle",
        default=None,
        help="Path to an existing live runtime suite bundle directory or parent directory.",
    )
    source_group.add_argument(
        "--run-live-suite",
        action="store_true",
        help="Run the live runtime suite before building the RFC-0028 proof pack.",
    )
    parser.add_argument(
        "--output-dir",
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory where sanitized RFC-0028 proof artifacts should be written.",
    )
    parser.add_argument(
        "--artifact-ref-prefix",
        default=None,
        help=(
            "Relative proof artifact reference prefix recorded inside proof-pack assets. "
            "Defaults to --output-dir when it is relative, otherwise "
            f"{_DEFAULT_OUTPUT_DIR}."
        ),
    )
    parser.add_argument(
        "--advise-base-url",
        default=os.getenv("LOTUS_ADVISE_BASE_URL", _DEFAULT_ADVISE_BASE_URL),
        help="lotus-advise base URL used for health, readiness, and capability probes.",
    )
    parser.add_argument(
        "--environment",
        default=os.getenv("LOTUS_ENVIRONMENT", "local"),
        help="Environment label recorded in proof metadata.",
    )
    parser.add_argument(
        "--service-version",
        default=os.getenv("LOTUS_ADVISE_SERVICE_VERSION", _DEFAULT_SERVICE_VERSION),
        help="lotus-advise service version recorded in proof metadata.",
    )
    parser.add_argument(
        "--repository-sha",
        default=None,
        help="lotus-advise commit SHA. Defaults to git rev-parse HEAD.",
    )
    parser.add_argument(
        "--correlation-id",
        default=None,
        help="Correlation id for this proof-capture run.",
    )
    parser.add_argument(
        "--skip-runtime-probe",
        action="store_true",
        help=(
            "Record NOT_PROBED runtime posture instead of calling health/readiness/capability APIs."
        ),
    )
    parser.add_argument(
        "--skip-degraded",
        action="store_true",
        help="When --run-live-suite is used, skip degraded-runtime drills.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    live_payload, result_ref, bundle_ref = _load_or_run_live_suite(args, output_dir)
    runtime_posture = (
        _not_probed_runtime_posture(args.advise_base_url, args.environment)
        if args.skip_runtime_probe
        else _probe_runtime_posture(args.advise_base_url, args.environment)
    )
    metadata = default_capture_metadata(
        repository_sha=args.repository_sha or _git_sha(),
        service_version=args.service_version,
        environment=args.environment,
        correlation_id=args.correlation_id or f"rfc0028-backend-proof-{uuid.uuid4().hex}",
        live_suite_result_ref=result_ref,
        live_suite_bundle_ref=bundle_ref,
    )
    bundle = build_backend_proof_capture(
        live_payload,
        metadata=metadata,
        runtime_posture=runtime_posture,
        output_ref_prefix=_artifact_ref_prefix_for(output_dir, args.artifact_ref_prefix),
    )
    written = write_backend_proof_capture_bundle(bundle, output_dir=output_dir)
    print(
        "RFC-0028 backend proof pack captured "
        f"(proof_pack={written['proof_pack']}, summary={written['summary']})"
    )


def _artifact_ref_prefix_for(output_dir: Path, configured_prefix: str | None) -> str:
    if configured_prefix is not None:
        return normalize_output_ref_prefix(configured_prefix)
    output_ref = _display_path(output_dir)
    try:
        return normalize_output_ref_prefix(output_ref)
    except ValueError:
        return _DEFAULT_OUTPUT_DIR


def _load_or_run_live_suite(
    args: argparse.Namespace,
    output_dir: Path,
) -> tuple[dict[str, Any], str, str | None]:
    if args.live_suite_json:
        result_path = Path(args.live_suite_json)
        return load_result_json(result_path), _display_path(result_path), None
    if args.live_suite_bundle:
        bundle_dir = resolve_bundle_dir(args.live_suite_bundle)
        result_path = bundle_dir / "result.json"
        return load_result_json(result_path), _display_path(result_path), _display_path(bundle_dir)
    if args.run_live_suite:
        result = validate_live_runtime_suite(include_degraded=not args.skip_degraded)
        live_bundle_dir = write_live_runtime_suite_bundle(result, output_dir=str(output_dir))
        if live_bundle_dir is None:
            raise RuntimeError("RFC0028_LIVE_SUITE_BUNDLE_NOT_WRITTEN")
        return (
            result_to_json_dict(result),
            _display_path(live_bundle_dir / "result.json"),
            _display_path(live_bundle_dir),
        )
    raise SystemExit(
        "Provide --live-suite-json, --live-suite-bundle, or --run-live-suite for repeatable proof."
    )


def _probe_runtime_posture(base_url: str, environment: str) -> BackendRuntimePosture:
    normalized_base_url = normalize_runtime_base_url(base_url)
    endpoints: list[RuntimeEndpointEvidence] = []
    with httpx.Client(timeout=10.0) as client:
        endpoints.append(_probe_endpoint(client, normalized_base_url, "/health"))
        endpoints.append(_probe_endpoint(client, normalized_base_url, "/health/live"))
        endpoints.append(_probe_endpoint(client, normalized_base_url, "/health/ready"))
        endpoints.append(_probe_endpoint(client, normalized_base_url, "/platform/capabilities"))
    return BackendRuntimePosture(
        base_url=normalized_base_url,
        environment=environment,
        endpoints=endpoints,
    )


def _probe_endpoint(
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


def _not_probed_runtime_posture(base_url: str, environment: str) -> BackendRuntimePosture:
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


def _elapsed_ms(started_at) -> int:
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


def _git_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _display_path(path: Path) -> str:
    return path.as_posix()


if __name__ == "__main__":
    main()
