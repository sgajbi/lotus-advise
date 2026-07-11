import json
from pathlib import Path

import pytest

from scripts.release_image_evidence import (
    ReleaseEvidence,
    _validate_production_manifest_policy,
    validate_image_labels,
    validate_static_release_contract,
    write_manifest,
)


def test_static_release_contract_passes_for_current_repo() -> None:
    assert validate_static_release_contract(Path(".")) == []


def test_production_manifest_policy_rejects_dev_hosts_plaintext_secrets_and_builds() -> None:
    compose_text = """
services:
  lotus-advise:
    build: .
    image: lotus-advise:latest
    environment:
      - LOTUS_CORE_BASE_URL=http://core-control.dev.lotus
      - PROPOSAL_POSTGRES_DSN=postgresql://advise:advise@postgres:5432/advise
      - POSTGRES_PASSWORD=advise
    extra_hosts:
      - "core-control.dev.lotus:host-gateway"
    healthcheck:
      test: ["CMD", "python", "-c", "http://127.0.0.1:8000/version"]
"""

    failures = _validate_production_manifest_policy(compose_text)

    assert "Production compose must not reference development DNS names." in failures
    assert "Production compose must not use host-gateway mappings." in failures
    assert "Production compose must not commit plaintext PostgreSQL DSNs." in failures
    assert "Production compose must not commit database passwords." in failures
    assert "Production compose must deploy a prebuilt release image, not build locally." in failures
    assert "Production compose must not use mutable latest tags." in failures
    assert "Production compose healthcheck must use readiness, not version metadata." in failures


def test_production_manifest_policy_requires_environment_injection() -> None:
    failures = _validate_production_manifest_policy("services:\n  lotus-advise: {}\n")

    assert "Production compose must require an immutable image digest ref." in failures
    assert "Production compose must require LOTUS_CORE_BASE_URL injection." in failures
    assert "Production compose must require LOTUS_CORE_QUERY_BASE_URL injection." in failures
    assert "Production compose must require LOTUS_RISK_BASE_URL injection." in failures
    assert "Production compose must require LOTUS_REPORT_BASE_URL injection." in failures
    assert "Production compose must require LOTUS_AI_BASE_URL injection." in failures
    assert "Production compose must require PROPOSAL_POSTGRES_DSN secret injection." in failures
    assert "Production compose must require POLICY_POSTGRES_DSN secret injection." in failures
    assert "Production compose must healthcheck the readiness endpoint." in failures


def test_image_label_validation_rejects_missing_required_label(monkeypatch) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        class Result:
            stdout = json.dumps(
                {
                    "org.opencontainers.image.title": "lotus-advise",
                    "org.opencontainers.image.source": "https://github.com/sgajbi/lotus-advise",
                    "org.opencontainers.image.revision": "abc123",
                    "org.opencontainers.image.ref.name": "main",
                    "org.opencontainers.image.version": "0.1.0",
                    "org.opencontainers.image.created": "2026-07-11T00:00:00Z",
                    "com.lotus.ci.run-id": "123",
                }
            )

        return Result()

    monkeypatch.setattr("scripts.release_image_evidence.subprocess.run", fake_run)

    failures = validate_image_labels(
        image_ref="lotus-advise:abc123",
        expected_commit="abc123",
        expected_repo_url="https://github.com/sgajbi/lotus-advise",
        expected_ci_run_id="123",
    )

    assert "Image lotus-advise:abc123 missing label com.lotus.image.digest" in failures


def test_release_manifest_records_digest_artifacts_and_deploy_policy(tmp_path: Path) -> None:
    output = tmp_path / "release-evidence.json"

    write_manifest(
        ReleaseEvidence(
            image_ref="ghcr.io/sgajbi/lotus-advise:abc123",
            image_digest="sha256:abc123",
            commit_sha="abc123",
            git_ref="main",
            repository_url="https://github.com/sgajbi/lotus-advise",
            service_version="0.1.0",
            build_timestamp_utc="2026-07-11T00:00:00Z",
            ci_pipeline_run_id="123",
            sbom_path="output/release/lotus-advise.spdx.json",
            vulnerability_scan_path="output/release/trivy-image-scan.json",
            signature_ref="ghcr.io/sgajbi/lotus-advise@sha256:abc123",
            provenance_attestation_ref="ghcr.io/sgajbi/lotus-advise@sha256:abc123",
        ),
        output,
    )

    manifest = json.loads(output.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "lotus.release-image-evidence.v1"
    assert manifest["git_commit_sha"] == "abc123"
    assert manifest["image"]["digest"] == "sha256:abc123"
    assert manifest["image"]["immutable_ref"] == "ghcr.io/sgajbi/lotus-advise:abc123@sha256:abc123"
    assert manifest["artifacts"]["sbom"] == "output/release/lotus-advise.spdx.json"
    assert (
        manifest["artifacts"]["license_ip_inventory"]
        == "docs/standards/license-ip-inventory.v1.json"
    )
    assert manifest["artifacts"]["vulnerability_scan"] == "output/release/trivy-image-scan.json"
    assert manifest["security_evidence"]["bandit_gate"] == "make bandit-severity-regression-gate"
    assert (
        manifest["security_evidence"]["bandit_baseline"]
        == "quality/bandit_security_baseline.v1.json"
    )
    assert manifest["security_evidence"]["dependency_lock"] == "make dependency-lock-gate"
    assert manifest["security_evidence"]["dependency_audit"] == "make security-audit"
    assert manifest["security_evidence"]["license_ip_gate"] == "make license-ip-gate"
    assert (
        manifest["security_evidence"]["license_ip_inventory"]
        == "docs/standards/license-ip-inventory.v1.json"
    )
    assert manifest["security_evidence"]["sbom"] == "output/release/lotus-advise.spdx.json"
    assert (
        manifest["security_evidence"]["container_vulnerability_scan"]
        == "output/release/trivy-image-scan.json"
    )
    assert manifest["deployment"]["deploy_by_digest"] is True
    assert manifest["deployment"]["same_image_promoted_across_environments"] is True
    assert manifest["version_endpoint"]["path"] == "/version"


def test_release_manifest_rejects_secret_named_keys(tmp_path: Path) -> None:
    output = tmp_path / "release-evidence.json"
    evidence = ReleaseEvidence(
        image_ref="ghcr.io/sgajbi/lotus-advise:abc123",
        image_digest="sha256:abc123",
        commit_sha="abc123",
        git_ref="main",
        repository_url="https://github.com/sgajbi/lotus-advise",
        service_version="0.1.0",
        build_timestamp_utc="2026-07-11T00:00:00Z",
        ci_pipeline_run_id="123",
        sbom_path="output/release/lotus-advise.spdx.json",
        vulnerability_scan_path="output/release/trivy-image-scan.json",
        signature_ref="ghcr.io/sgajbi/lotus-advise@sha256:abc123",
        provenance_attestation_ref="ghcr.io/sgajbi/lotus-advise@sha256:abc123",
    )

    manifest = evidence.as_manifest()
    manifest["secret_token"] = "not-allowed"

    with pytest.raises(ValueError):
        from scripts.release_image_evidence import _validate_manifest_secret_names

        _validate_manifest_secret_names(manifest)

    assert not output.exists()
