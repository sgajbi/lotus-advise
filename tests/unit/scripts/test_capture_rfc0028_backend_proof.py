from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from scripts.capture_rfc0028_backend_proof import (
    _DEFAULT_OUTPUT_DIR,
    _artifact_ref_prefix_for,
    _not_probed_runtime_posture,
    _probe_endpoint,
    _probe_runtime_posture,
)
from scripts.rfc0028_backend_proof_writer import write_backend_proof_capture_bundle
from src.core.bank_demo_proof import (
    BackendRuntimePosture,
    RuntimeEndpointEvidence,
    build_backend_proof_capture,
    default_capture_metadata,
)
from tests.unit.advisory.engine.test_engine_bank_demo_proof_capture import _live_runtime_payload


def test_backend_proof_capture_writer_emits_sanitized_artifact_set(tmp_path) -> None:
    bundle = build_backend_proof_capture(
        _live_runtime_payload(),
        metadata=default_capture_metadata(
            repository_sha="abc123",
            service_version="0.1.0",
            environment="local",
            correlation_id="corr-rfc0028-writer",
            generated_at=datetime(2026, 5, 28, 10, 0, tzinfo=UTC),
            live_suite_result_ref="output/rfc0028/source/result.json",
        ),
        runtime_posture=BackendRuntimePosture(
            base_url="http://advise.dev.lotus",
            environment="local",
            endpoints=[
                RuntimeEndpointEvidence(
                    endpoint="/health",
                    http_status=200,
                    posture="READY",
                    latency_ms=5,
                    summary={"status": "ok"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/health/live",
                    http_status=200,
                    posture="READY",
                    latency_ms=6,
                    summary={"status": "live"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/health/ready",
                    http_status=200,
                    posture="READY",
                    latency_ms=6,
                    summary={"status": "ready"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/platform/capabilities",
                    http_status=200,
                    posture="READY",
                    latency_ms=9,
                    summary={
                        "feature_keys": ["advisory.proposals.lifecycle"],
                        "workflow_keys": ["advisory_proposal_lifecycle"],
                    },
                ),
            ],
        ),
    )

    paths = write_backend_proof_capture_bundle(bundle, output_dir=tmp_path)

    expected = {
        "metadata",
        "scenario_contract",
        "supported_claim_register",
        "proof_pack",
        "document_proof_summary",
        "journey_integration_proof_summary",
        "commercial_material_pack",
        "runtime_posture",
        "sanitized_runtime_summary",
        "material_field_review",
        "summary",
        "manifest",
    }
    assert set(paths) == expected
    for path in paths.values():
        assert path.exists()

    proof_pack = json.loads(paths["proof_pack"].read_text(encoding="utf-8"))
    document_proof = json.loads(paths["document_proof_summary"].read_text(encoding="utf-8"))
    integration_proof = json.loads(
        paths["journey_integration_proof_summary"].read_text(encoding="utf-8")
    )
    commercial_pack = json.loads(paths["commercial_material_pack"].read_text(encoding="utf-8"))
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    sanitized_summary = paths["sanitized_runtime_summary"].read_text(encoding="utf-8")
    runtime_posture = json.loads(paths["runtime_posture"].read_text(encoding="utf-8"))
    markdown_summary = paths["summary"].read_text(encoding="utf-8")

    assert proof_pack["client_ready_posture"] == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert proof_pack["assets"][1]["asset_id"] == "document_proof_summary"
    assert proof_pack["assets"][2]["asset_id"] == "journey_integration_proof_summary"
    assert any(asset["asset_id"] == "commercial_material_pack" for asset in proof_pack["assets"])
    assert document_proof["client_ready_publication"] == "BLOCKED"
    assert {item["document_family"] for item in document_proof["documents"]} == {
        "PROPOSAL_MEMO",
        "POLICY_SIGN_OFF",
    }
    assert integration_proof["policy_evidence"]["client_ready_publication"] == "BLOCKED"
    assert "advisory.advisor_cockpit" in integration_proof["required_workbench_panels"]
    assert commercial_pack["publication_posture"] == "CUSTOMER_CONSUMABLE_WITH_BOUNDARIES"
    assert "commercial_rfp_security_material_available" in commercial_pack["required_claim_ids"]
    assert manifest["artifact_family"] == "rfc0028.backend-proof-capture.v1"
    assert manifest["artifacts"]["metadata"] == "metadata.json"
    assert manifest["artifacts"]["proof_pack"] == "proof-pack.json"
    assert all(
        str(tmp_path).replace("\\", "/") not in ref for ref in manifest["artifacts"].values()
    )
    assert "BANK_DEMO_PROOF_PACK_CREATED" in markdown_summary
    assert "AI, Policy, And Cockpit Integration Proof" in markdown_summary
    assert "Commercial, RFP, Security, Architecture, ROI, And Demo Material" in markdown_summary
    assert runtime_posture["endpoints"][0]["latency_ms"] == 5
    assert "`5 ms`" in markdown_summary
    assert "sha256:memo" not in sanitized_summary
    assert "source_input_hash" not in sanitized_summary


def test_runtime_probe_redacts_sensitive_material_and_records_latency() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/platform/capabilities"
        return httpx.Response(
            200,
            json={
                "features": [{"key": "advisory.bank_demo_proof"}],
                "workflows": [{"workflow_key": "advisory_bank_demo_proof"}],
                "readiness": {
                    "operational_ready": True,
                    "degraded": False,
                    "degraded_reasons": [
                        "see https://advise.dev.lotus/ready?token=should-not-leak"
                    ],
                },
                "authorization": "Bearer should-not-leak",
                "trace_id": "trace-should-not-leak",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")

    evidence = _probe_endpoint(client, "https://advise.dev.lotus", "/platform/capabilities")

    assert evidence.posture == "READY"
    assert evidence.http_status == 200
    assert evidence.latency_ms is not None
    assert evidence.summary["feature_keys"] == ["advisory.bank_demo_proof"]
    assert "token" not in evidence.summary["degraded_reasons"][0]
    assert "authorization" not in evidence.summary
    assert "trace_id" not in evidence.summary


def test_runtime_probe_rejects_unsafe_base_url_before_capture() -> None:
    with pytest.raises(ValueError, match="credentials, query, or fragment"):
        _probe_runtime_posture("https://user:secret@advise.dev.lotus?token=abc", "local")

    with pytest.raises(ValueError, match="credentials, query, or fragment"):
        _not_probed_runtime_posture("https://advise.dev.lotus#token=abc", "local")

    posture = _not_probed_runtime_posture("https://advise.dev.lotus/runtime/", "local")

    assert posture.base_url == "https://advise.dev.lotus/runtime"


def test_artifact_ref_prefix_remains_relative_for_absolute_output_dir(tmp_path) -> None:
    assert _artifact_ref_prefix_for(tmp_path, None) == _DEFAULT_OUTPUT_DIR
    assert (
        _artifact_ref_prefix_for(tmp_path, "output/rfc0028/custom-proof")
        == "output/rfc0028/custom-proof"
    )

    with pytest.raises(ValueError, match="sensitive material"):
        _artifact_ref_prefix_for(tmp_path, "output/rfc0028/token-proof")
