from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import cast

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.rfc0028_backend_proof_writer import (  # noqa: E402
    write_backend_proof_capture_bundle,
)
from scripts.rfc0028_live_suite_source import (  # noqa: E402
    display_path,
    load_or_run_live_suite,
)
from scripts.rfc0028_runtime_probe import (  # noqa: E402
    not_probed_runtime_posture,
    probe_runtime_posture,
)
from src.core.bank_demo_proof import (  # noqa: E402
    build_backend_proof_capture,
    default_capture_metadata,
)
from src.core.bank_demo_proof.artifact_refs import normalize_output_ref_prefix  # noqa: E402
from src.core.common.sensitive_error_details import contains_sensitive_error_detail  # noqa: E402

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
    live_payload, result_ref, bundle_ref = load_or_run_live_suite(
        live_suite_json=args.live_suite_json,
        live_suite_bundle=args.live_suite_bundle,
        run_live_suite=args.run_live_suite,
        skip_degraded=args.skip_degraded,
        output_dir=output_dir,
    )
    runtime_posture = (
        not_probed_runtime_posture(args.advise_base_url, args.environment)
        if args.skip_runtime_probe
        else probe_runtime_posture(args.advise_base_url, args.environment)
    )
    try:
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
    except ValueError as exc:
        raise SystemExit(_safe_cli_error_detail(str(exc))) from None
    print(
        "RFC-0028 backend proof pack captured "
        f"(proof_pack={written['proof_pack']}, summary={written['summary']})"
    )


def _artifact_ref_prefix_for(output_dir: Path, configured_prefix: str | None) -> str:
    if configured_prefix is not None:
        return cast(str, normalize_output_ref_prefix(configured_prefix))
    output_ref = display_path(output_dir)
    try:
        return cast(str, normalize_output_ref_prefix(output_ref))
    except ValueError:
        return _DEFAULT_OUTPUT_DIR


def _git_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _safe_cli_error_detail(error_detail: str) -> str:
    if contains_sensitive_error_detail(error_detail):
        return "RFC0028_BACKEND_PROOF_CAPTURE_FAILED: source evidence failed validation"
    return error_detail


if __name__ == "__main__":
    main()
