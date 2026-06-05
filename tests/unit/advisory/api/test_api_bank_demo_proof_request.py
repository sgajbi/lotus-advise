from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.api.observability import correlation_id_var
from src.api.routers.bank_demo_proof_request import (
    BankDemoProofCaptureRequest,
    runtime_correlation_id,
    runtime_environment,
    runtime_repository_sha,
    runtime_service_version,
)
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import (
    _live_runtime_payload,
    _runtime_posture,
)


def test_bank_demo_proof_request_rejects_sensitive_local_artifact_refs() -> None:
    normalized = BankDemoProofCaptureRequest(
        live_runtime_payload=_live_runtime_payload(),
        runtime_posture=_runtime_posture(),
        live_suite_result_ref=" output\\live-runtime-suite\\result.json ",
        output_ref_prefix=" output\\rfc0028\\backend-proof\\ ",
    )

    assert normalized.live_suite_result_ref == "output/live-runtime-suite/result.json"
    assert normalized.output_ref_prefix == "output/rfc0028/backend-proof"

    with pytest.raises(ValidationError, match="live_suite_result_ref must not include URL"):
        BankDemoProofCaptureRequest(
            live_runtime_payload=_live_runtime_payload(),
            runtime_posture=_runtime_posture(),
            live_suite_result_ref="output/live-runtime-suite/result.json?token=should-not-leak",
        )

    with pytest.raises(ValidationError, match="output_ref_prefix cannot contain"):
        BankDemoProofCaptureRequest(
            live_runtime_payload=_live_runtime_payload(),
            runtime_posture=_runtime_posture(),
            output_ref_prefix="../output/rfc0028/backend-proof",
        )

    with pytest.raises(ValidationError, match="live_suite_bundle_ref cannot contain"):
        BankDemoProofCaptureRequest(
            live_runtime_payload=_live_runtime_payload(),
            runtime_posture=_runtime_posture(),
            live_suite_bundle_ref="output/rfc0028/provider output",
        )

    with pytest.raises(ValidationError, match="output_ref_prefix cannot contain"):
        BankDemoProofCaptureRequest(
            live_runtime_payload=_live_runtime_payload(),
            runtime_posture=_runtime_posture(),
            output_ref_prefix="output/rfc0028/trace-id",
        )


def test_bank_demo_proof_runtime_metadata_prefers_request_then_environment(monkeypatch) -> None:
    monkeypatch.setenv("LOTUS_ADVISE_COMMIT_SHA", "env-sha-456")
    monkeypatch.setenv("SERVICE_VERSION", "9.9.9")
    monkeypatch.setenv("ENVIRONMENT", "staging")

    assert runtime_repository_sha(" request-sha-123 ") == "request-sha-123"
    assert runtime_repository_sha(None) == "env-sha-456"
    assert runtime_service_version(None) == "9.9.9"
    assert runtime_environment(None) == "staging"


def test_bank_demo_proof_runtime_metadata_uses_governed_fallbacks(monkeypatch) -> None:
    monkeypatch.delenv("LOTUS_ADVISE_COMMIT_SHA", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("SERVICE_VERSION", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    assert runtime_repository_sha(None) == "runtime-unknown"
    assert runtime_service_version(None) == "0.1.0"
    assert runtime_environment(None) == "local"


def test_bank_demo_proof_correlation_uses_request_context_without_sensitive_material() -> None:
    token = correlation_id_var.set("corr-context-123")
    try:
        assert runtime_correlation_id(None) == "corr-context-123"
        assert runtime_correlation_id(" corr-request-456 ") == "corr-request-456"
        with pytest.raises(ValueError, match="sensitive material"):
            runtime_correlation_id("corr-token-should-not-leak")
        with pytest.raises(ValueError, match="sensitive material"):
            runtime_correlation_id("trace id trace-should-not-leak")
    finally:
        correlation_id_var.reset(token)


def test_bank_demo_proof_runtime_metadata_rejects_provider_and_raw_payload_terms() -> None:
    with pytest.raises(ValueError, match="sensitive material"):
        runtime_environment("provider output included internal model detail")

    with pytest.raises(ValueError, match="sensitive material"):
        runtime_service_version("raw-payload-build")

    with pytest.raises(ValueError, match="sensitive material"):
        runtime_repository_sha("raw source sha")
