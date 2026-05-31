from __future__ import annotations

from src.core.bank_demo_proof.proof_assets import build_backend_proof_assets
from src.core.common.canonical import hash_canonical_payload


def test_backend_proof_assets_preserve_commit_and_local_evidence_boundaries() -> None:
    sanitized_summary = {"scenario_id": "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL"}
    document_payload = {"documents": [{"document_family": "PROPOSAL_MEMO"}]}
    integration_payload = {"proof_posture": "IMPLEMENTATION_BACKED"}
    commercial_payload = {"materials": [{"material_id": "demo_script"}]}
    material_reviews = [{"review_id": "policy_client_ready", "review_posture": "PASS"}]
    runtime_posture = {"environment": "local"}

    assets = build_backend_proof_assets(
        output_ref_prefix="output/rfc0028/backend-proof",
        sanitized_summary=sanitized_summary,
        document_proof_payload=document_payload,
        integration_proof_payload=integration_payload,
        commercial_material_payload=commercial_payload,
        material_review_payload=material_reviews,
        runtime_posture_payload=runtime_posture,
        live_suite_bundle_ref=None,
        live_suite_result_ref="output/rfc0028/source/result.json",
    )

    by_id = {asset.asset_id: asset for asset in assets}

    assert set(by_id) == {
        "sanitized_runtime_summary",
        "document_proof_summary",
        "journey_integration_proof_summary",
        "material_field_review",
        "commercial_material_pack",
        "runtime_posture",
        "source_live_runtime_bundle",
    }
    assert by_id["commercial_material_pack"].commit_allowed is True
    assert by_id["commercial_material_pack"].access_class == "CUSTOMER_CONSUMABLE_SUMMARY"
    assert by_id["source_live_runtime_bundle"].access_class == "LOCAL_ONLY_RUNTIME_EVIDENCE"
    assert by_id["source_live_runtime_bundle"].uri == "output/rfc0028/source/result.json"
    assert by_id["sanitized_runtime_summary"].content_hash == hash_canonical_payload(
        sanitized_summary
    )
    assert by_id["material_field_review"].content_hash == hash_canonical_payload(material_reviews)


def test_backend_proof_assets_prefer_live_suite_bundle_ref_over_result_ref() -> None:
    assets = build_backend_proof_assets(
        output_ref_prefix="output/rfc0028/backend-proof",
        sanitized_summary={},
        document_proof_payload={},
        integration_proof_payload={},
        commercial_material_payload={},
        material_review_payload=[],
        runtime_posture_payload={},
        live_suite_bundle_ref="output/rfc0028/source/bundle",
        live_suite_result_ref="output/rfc0028/source/result.json",
    )

    source_asset = next(asset for asset in assets if asset.asset_id == "source_live_runtime_bundle")

    assert source_asset.uri == "output/rfc0028/source/bundle"
