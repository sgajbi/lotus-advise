from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

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
from scripts.rfc0028_runtime_probe import (  # noqa: E402
    not_probed_runtime_posture,
    probe_runtime_posture,
)
from scripts.validate_live_runtime_suite import validate_live_runtime_suite  # noqa: E402
from src.core.bank_demo_proof import (  # noqa: E402
    build_backend_proof_capture,
    default_capture_metadata,
    normalize_output_ref_prefix,
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
        not_probed_runtime_posture(args.advise_base_url, args.environment)
        if args.skip_runtime_probe
        else probe_runtime_posture(args.advise_base_url, args.environment)
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
