from __future__ import annotations

from typing import Any

from src.core.bank_demo_proof.models import ProofAsset
from src.core.common.canonical import hash_canonical_payload


def build_backend_proof_assets(
    *,
    output_ref_prefix: str,
    sanitized_summary: dict[str, Any],
    document_proof_payload: dict[str, Any],
    integration_proof_payload: dict[str, Any],
    commercial_material_payload: dict[str, Any],
    material_review_payload: list[dict[str, Any]],
    runtime_posture_payload: dict[str, Any],
    live_suite_bundle_ref: str | None,
    live_suite_result_ref: str | None,
) -> list[ProofAsset]:
    return [
        ProofAsset(
            asset_id="sanitized_runtime_summary",
            asset_type="LIVE_VALIDATION_SUMMARY",
            source_repository="lotus-advise",
            uri=f"{output_ref_prefix}/sanitized-runtime-summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=[
                "backend_proof_capture_repeatable",
                "advisor_journey_backend_evidence_available",
            ],
            content_hash=hash_canonical_payload(sanitized_summary),
            commit_allowed=False,
        ),
        ProofAsset(
            asset_id="document_proof_summary",
            asset_type="REPORT_PACKAGE_SUMMARY",
            source_repository="lotus-advise",
            uri=f"{output_ref_prefix}/document-proof-summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=[
                "backend_proof_capture_repeatable",
                "advisor_use_document_proof_available",
            ],
            content_hash=hash_canonical_payload(document_proof_payload),
            commit_allowed=False,
        ),
        ProofAsset(
            asset_id="journey_integration_proof_summary",
            asset_type="GOVERNANCE_INTEGRATION_SUMMARY",
            source_repository="lotus-advise",
            uri=f"{output_ref_prefix}/journey-integration-proof-summary.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=[
                "backend_proof_capture_repeatable",
                "ai_policy_cockpit_proof_integrated",
            ],
            content_hash=hash_canonical_payload(integration_proof_payload),
            commit_allowed=False,
        ),
        ProofAsset(
            asset_id="material_field_review",
            asset_type="API_RESPONSE_SUMMARY",
            source_repository="lotus-advise",
            uri=f"{output_ref_prefix}/material-field-review.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=[
                "backend_proof_capture_repeatable",
                "advisor_journey_backend_evidence_available",
                "ai_policy_cockpit_proof_integrated",
                "degraded_runtime_boundary_evidence_available",
            ],
            content_hash=hash_canonical_payload(material_review_payload),
            commit_allowed=False,
        ),
        ProofAsset(
            asset_id="commercial_material_pack",
            asset_type="COMMERCIAL_DOCUMENT",
            source_repository="lotus-advise",
            uri="docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
            access_class="CUSTOMER_CONSUMABLE_SUMMARY",
            retention_class="COMMIT_SOURCE",
            evidence_refs=[
                "commercial_rfp_security_material_available",
                "client_ready_publication_blocked",
            ],
            content_hash=hash_canonical_payload(commercial_material_payload),
            commit_allowed=True,
        ),
        ProofAsset(
            asset_id="runtime_posture",
            asset_type="SECURITY_CHECK_SUMMARY",
            source_repository="lotus-advise",
            uri=f"{output_ref_prefix}/runtime-posture.json",
            access_class="COMMIT_SAFE_SUMMARY",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=["backend_proof_capture_repeatable"],
            content_hash=hash_canonical_payload(runtime_posture_payload),
            commit_allowed=False,
        ),
        ProofAsset(
            asset_id="source_live_runtime_bundle",
            asset_type="LOCAL_RUNTIME_BUNDLE",
            source_repository="lotus-advise",
            uri=live_suite_bundle_ref
            or live_suite_result_ref
            or f"{output_ref_prefix}/source-live-runtime-suite",
            access_class="LOCAL_ONLY_RUNTIME_EVIDENCE",
            retention_class="LOCAL_EVIDENCE_BUNDLE",
            evidence_refs=["backend_proof_capture_repeatable"],
            commit_allowed=False,
        ),
    ]
