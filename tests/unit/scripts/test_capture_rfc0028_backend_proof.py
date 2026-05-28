from __future__ import annotations

import json
from datetime import UTC, datetime

from scripts.capture_rfc0028_backend_proof import write_backend_proof_capture_bundle
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
                    summary={"status": "ok"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/health/live",
                    http_status=200,
                    posture="READY",
                    summary={"status": "live"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/health/ready",
                    http_status=200,
                    posture="READY",
                    summary={"status": "ready"},
                ),
                RuntimeEndpointEvidence(
                    endpoint="/platform/capabilities",
                    http_status=200,
                    posture="READY",
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
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    sanitized_summary = paths["sanitized_runtime_summary"].read_text(encoding="utf-8")
    markdown_summary = paths["summary"].read_text(encoding="utf-8")

    assert proof_pack["client_ready_posture"] == "CLIENT_READY_PUBLICATION_BLOCKED"
    assert proof_pack["assets"][1]["asset_id"] == "document_proof_summary"
    assert proof_pack["assets"][2]["asset_id"] == "journey_integration_proof_summary"
    assert document_proof["client_ready_publication"] == "BLOCKED"
    assert {item["document_family"] for item in document_proof["documents"]} == {
        "PROPOSAL_MEMO",
        "POLICY_SIGN_OFF",
    }
    assert integration_proof["policy_evidence"]["client_ready_publication"] == "BLOCKED"
    assert "advisory.advisor_cockpit" in integration_proof["required_workbench_panels"]
    assert manifest["artifact_family"] == "rfc0028.backend-proof-capture.v1"
    assert "BANK_DEMO_PROOF_PACK_CREATED" in markdown_summary
    assert "AI, Policy, And Cockpit Integration Proof" in markdown_summary
    assert "sha256:memo" not in sanitized_summary
    assert "source_input_hash" not in sanitized_summary
