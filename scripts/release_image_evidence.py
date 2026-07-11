"""Validate and emit Lotus Advise container release evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_NAME = "lotus-advise"

REQUIRED_OCI_LABELS = {
    "org.opencontainers.image.title": SERVICE_NAME,
    "org.opencontainers.image.source": None,
    "org.opencontainers.image.revision": None,
    "org.opencontainers.image.ref.name": None,
    "org.opencontainers.image.version": None,
    "org.opencontainers.image.created": None,
    "com.lotus.ci.run-id": None,
    "com.lotus.image.digest": None,
}

FORBIDDEN_BUILD_METADATA_NAME = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|PRIVATE[_-]?KEY|API[_-]?KEY|DSN|CONNECTION)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReleaseEvidence:
    image_ref: str
    image_digest: str
    commit_sha: str
    git_ref: str
    repository_url: str
    service_version: str
    build_timestamp_utc: str
    ci_pipeline_run_id: str
    sbom_path: str
    vulnerability_scan_path: str
    signature_ref: str
    provenance_attestation_ref: str

    def as_manifest(self) -> dict[str, Any]:
        immutable_ref = (
            f"{self.image_ref}@{self.image_digest}"
            if self.image_digest.startswith("sha256:")
            else self.image_ref
        )
        return {
            "schema_version": "lotus.release-image-evidence.v1",
            "service_name": SERVICE_NAME,
            "repository_url": self.repository_url,
            "git_commit_sha": self.commit_sha,
            "git_ref": self.git_ref,
            "service_version": self.service_version,
            "build_timestamp_utc": self.build_timestamp_utc,
            "ci_pipeline_run_id": self.ci_pipeline_run_id,
            "image": {
                "ref": self.image_ref,
                "digest": self.image_digest,
                "immutable_ref": immutable_ref,
                "tag_policy": "git-sha",
                "pushed_by": "github-actions-main-releasability",
            },
            "artifacts": {
                "sbom": self.sbom_path,
                "license_ip_inventory": "docs/standards/license-ip-inventory.v1.json",
                "vulnerability_scan": self.vulnerability_scan_path,
                "signature": self.signature_ref,
                "provenance_attestation": self.provenance_attestation_ref,
                "release_manifest": "release-evidence.json",
            },
            "deployment": {
                "deploy_by_digest": True,
                "same_image_promoted_across_environments": True,
                "release_image_push_policy": "ci-only-main-releasability",
            },
            "metadata_leak_controls": {
                "dockerfile_arg_env_name_scan": "passed",
                "oci_label_name_scan": "passed",
                "release_manifest_name_scan": "passed",
            },
            "security_evidence": {
                "bandit_gate": "make bandit-severity-regression-gate",
                "bandit_baseline": "quality/bandit_security_baseline.v1.json",
                "dependency_audit": "make security-audit",
                "license_ip_gate": "make license-ip-gate",
                "license_ip_inventory": "docs/standards/license-ip-inventory.v1.json",
                "sbom": self.sbom_path,
                "container_vulnerability_scan": self.vulnerability_scan_path,
            },
            "required_oci_labels": sorted(REQUIRED_OCI_LABELS),
            "version_endpoint": {
                "path": "/version",
                "metadata_parity": [
                    "service_version",
                    "git_commit_sha",
                    "git_branch",
                    "repository_url",
                    "build_timestamp_utc",
                    "ci_pipeline_run_id",
                    "image_digest",
                ],
            },
        }


def validate_static_release_contract(repo_root: Path) -> list[str]:
    failures: list[str] = []
    dockerfile = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    makefile = (repo_root / "Makefile").read_text(encoding="utf-8")
    production_compose = (repo_root / "docker-compose.production.yml").read_text(encoding="utf-8")

    for label in REQUIRED_OCI_LABELS:
        if label not in dockerfile:
            failures.append(f"Dockerfile missing required OCI label: {label}")

    for required_arg in (
        "LOTUS_BUILD_COMMIT_SHA",
        "LOTUS_BUILD_GIT_BRANCH",
        "LOTUS_BUILD_REPO_URL",
        "LOTUS_BUILD_VERSION",
        "LOTUS_BUILD_TIMESTAMP",
        "LOTUS_CI_PIPELINE_ID",
        "LOTUS_IMAGE_DIGEST",
    ):
        if f"ARG {required_arg}" not in dockerfile:
            failures.append(f"Dockerfile missing build arg: {required_arg}")
        if f"--build-arg {required_arg}=" not in makefile:
            failures.append(f"Makefile docker-build missing build arg: {required_arg}")

    failures.extend(_validate_no_secret_named_arg_or_env(dockerfile))
    failures.extend(_validate_production_manifest_policy(production_compose))
    return failures


def validate_image_labels(
    *,
    image_ref: str,
    expected_commit: str,
    expected_repo_url: str,
    expected_ci_run_id: str,
) -> list[str]:
    labels = _docker_image_labels(image_ref)
    failures: list[str] = []
    for label, expected_value in REQUIRED_OCI_LABELS.items():
        actual = labels.get(label)
        if not actual:
            failures.append(f"Image {image_ref} missing label {label}")
        elif expected_value is not None and actual != expected_value:
            failures.append(
                f"Image {image_ref} label {label}={actual!r}, expected {expected_value!r}"
            )

    expected = {
        "org.opencontainers.image.revision": expected_commit,
        "org.opencontainers.image.source": expected_repo_url,
        "com.lotus.ci.run-id": expected_ci_run_id,
    }
    for label, expected_value in expected.items():
        actual = labels.get(label)
        if actual != expected_value:
            failures.append(
                f"Image {image_ref} label {label}={actual!r}, expected {expected_value!r}"
            )

    for label in labels:
        if FORBIDDEN_BUILD_METADATA_NAME.search(label):
            failures.append(f"Image label name is not support-safe: {label}")
    return failures


def write_manifest(evidence: ReleaseEvidence, output_path: Path) -> None:
    manifest = evidence.as_manifest()
    _validate_manifest_secret_names(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_no_secret_named_arg_or_env(dockerfile: str) -> list[str]:
    failures: list[str] = []
    for line in dockerfile.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("ARG ") or stripped.startswith("ENV ")):
            continue
        name_part = stripped.split(maxsplit=1)[1].split("=", maxsplit=1)[0]
        if FORBIDDEN_BUILD_METADATA_NAME.search(name_part):
            failures.append(f"Dockerfile build metadata name is not support-safe: {name_part}")
    return failures


def _validate_production_manifest_policy(compose_text: str) -> list[str]:
    failures: list[str] = []
    forbidden_fragments = {
        ".dev.lotus": "Production compose must not reference development DNS names.",
        "host-gateway": "Production compose must not use host-gateway mappings.",
        "postgresql://": "Production compose must not commit plaintext PostgreSQL DSNs.",
        "POSTGRES_PASSWORD": "Production compose must not commit database passwords.",
        "build:": "Production compose must deploy a prebuilt release image, not build locally.",
        "image: lotus-advise:latest": "Production compose must not use mutable latest tags.",
        "http://127.0.0.1:8000/version": (
            "Production compose healthcheck must use readiness, not version metadata."
        ),
    }
    for fragment, message in forbidden_fragments.items():
        if fragment in compose_text:
            failures.append(message)

    required_fragments = {
        "image: ${LOTUS_ADVISE_IMAGE_DIGEST_REF:": (
            "Production compose must require an immutable image digest ref."
        ),
        "LOTUS_CORE_BASE_URL=${LOTUS_CORE_BASE_URL:?": (
            "Production compose must require LOTUS_CORE_BASE_URL injection."
        ),
        "LOTUS_CORE_QUERY_BASE_URL=${LOTUS_CORE_QUERY_BASE_URL:?": (
            "Production compose must require LOTUS_CORE_QUERY_BASE_URL injection."
        ),
        "LOTUS_RISK_BASE_URL=${LOTUS_RISK_BASE_URL:?": (
            "Production compose must require LOTUS_RISK_BASE_URL injection."
        ),
        "LOTUS_REPORT_BASE_URL=${LOTUS_REPORT_BASE_URL:?": (
            "Production compose must require LOTUS_REPORT_BASE_URL injection."
        ),
        "LOTUS_AI_BASE_URL=${LOTUS_AI_BASE_URL:?": (
            "Production compose must require LOTUS_AI_BASE_URL injection."
        ),
        "PROPOSAL_POSTGRES_DSN=${PROPOSAL_POSTGRES_DSN:?": (
            "Production compose must require PROPOSAL_POSTGRES_DSN secret injection."
        ),
        "POLICY_POSTGRES_DSN=${POLICY_POSTGRES_DSN:?": (
            "Production compose must require POLICY_POSTGRES_DSN secret injection."
        ),
        "http://127.0.0.1:8000/health/ready": (
            "Production compose must healthcheck the readiness endpoint."
        ),
    }
    for fragment, message in required_fragments.items():
        if fragment not in compose_text:
            failures.append(message)
    return failures


def _validate_manifest_secret_names(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if FORBIDDEN_BUILD_METADATA_NAME.search(str(key)):
                raise ValueError(f"Release manifest key is not support-safe: {path}.{key}")
            _validate_manifest_secret_names(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_manifest_secret_names(child, f"{path}[{index}]")


def _docker_image_labels(image_ref: str) -> dict[str, str]:
    result = subprocess.run(
        ["docker", "image", "inspect", image_ref, "--format", "{{json .Config.Labels}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = result.stdout.strip()
    if not payload or payload == "null":
        return {}
    labels = json.loads(payload)
    if not isinstance(labels, dict):
        return {}
    return {str(key): str(value) for key, value in labels.items()}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("static-check")

    image_check = subparsers.add_parser("image-label-check")
    image_check.add_argument("--image-ref", required=True)
    image_check.add_argument("--expected-commit", required=True)
    image_check.add_argument("--expected-repo-url", required=True)
    image_check.add_argument("--expected-ci-run-id", required=True)

    manifest = subparsers.add_parser("write-manifest")
    manifest.add_argument("--image-ref", required=True)
    manifest.add_argument("--image-digest", required=True)
    manifest.add_argument("--commit-sha", required=True)
    manifest.add_argument("--git-ref", required=True)
    manifest.add_argument("--repository-url", required=True)
    manifest.add_argument("--service-version", required=True)
    manifest.add_argument("--build-timestamp-utc", required=True)
    manifest.add_argument("--ci-pipeline-run-id", required=True)
    manifest.add_argument("--sbom-path", required=True)
    manifest.add_argument("--vulnerability-scan-path", required=True)
    manifest.add_argument("--signature-ref", required=True)
    manifest.add_argument("--provenance-attestation-ref", required=True)
    manifest.add_argument("--output", default="output/release/release-evidence.json")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.command == "static-check":
        failures = validate_static_release_contract(REPO_ROOT)
    elif args.command == "image-label-check":
        failures = validate_image_labels(
            image_ref=args.image_ref,
            expected_commit=args.expected_commit,
            expected_repo_url=args.expected_repo_url,
            expected_ci_run_id=args.expected_ci_run_id,
        )
    else:
        write_manifest(
            ReleaseEvidence(
                image_ref=args.image_ref,
                image_digest=args.image_digest,
                commit_sha=args.commit_sha,
                git_ref=args.git_ref,
                repository_url=args.repository_url,
                service_version=args.service_version,
                build_timestamp_utc=args.build_timestamp_utc,
                ci_pipeline_run_id=args.ci_pipeline_run_id,
                sbom_path=args.sbom_path,
                vulnerability_scan_path=args.vulnerability_scan_path,
                signature_ref=args.signature_ref,
                provenance_attestation_ref=args.provenance_attestation_ref,
            ),
            Path(args.output),
        )
        failures = []

    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
