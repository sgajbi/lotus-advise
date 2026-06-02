from __future__ import annotations

from src.core.bank_demo_proof.commercial_materials import CommercialMaterial

REQUIRED_COMMERCIAL_CLAIM_IDS: list[str] = [
    "backend_proof_capture_repeatable",
    "advisor_journey_product_surface_proven",
    "advisor_use_document_proof_available",
    "degraded_runtime_boundary_evidence_available",
    "ai_policy_cockpit_proof_integrated",
    "commercial_rfp_security_material_available",
    "client_ready_publication_blocked",
]

BLOCKED_COMMERCIAL_CLAIMS: list[str] = [
    "client_ready_publication",
    "external_client_communication",
    "completed_policy_approval_or_sign_off",
    "legal_or_regulatory_advice",
    "bank_specific_security_attestation",
    "oms_order_fill_or_settlement",
]


def build_commercial_materials(source_ref: str) -> list[CommercialMaterial]:
    blocked = BLOCKED_COMMERCIAL_CLAIMS
    return [
        CommercialMaterial(
            material_id="product_one_pager",
            title="Private-banking advisory proof one-pager",
            material_type="PRODUCT_ONE_PAGER",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "advisor_journey_product_surface_proven",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "CLIENT_DEMO"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="rfp_response_pack",
            title="RFP response pack",
            material_type="RFP_RESPONSE",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "backend_proof_capture_repeatable",
                "degraded_runtime_boundary_evidence_available",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "RFP_SECURITY"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="security_posture_pack",
            title="Security and governance posture pack",
            material_type="SECURITY_PACK",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "degraded_runtime_boundary_evidence_available",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["PRE_SALES", "RFP_SECURITY", "OPERATIONS"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="architecture_outline",
            title="Deck-ready architecture outline",
            material_type="ARCHITECTURE_OUTLINE",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "ai_policy_cockpit_proof_integrated",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "DEVELOPER", "OPERATIONS"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="demo_script",
            title="Bank-demo script and talk track",
            material_type="DEMO_SCRIPT",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "advisor_use_document_proof_available",
                "ai_policy_cockpit_proof_integrated",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "CLIENT_DEMO", "OPERATIONS"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="proof_pack_interpretation_guide",
            title="Proof-pack interpretation guide",
            material_type="PROOF_GUIDE",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "backend_proof_capture_repeatable",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["DEVELOPER", "OPERATIONS", "PRE_SALES"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="roi_story",
            title="Implementation-backed ROI story",
            material_type="ROI_STORY",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "advisor_journey_product_surface_proven",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="supported_feature_matrix",
            title="Supported versus blocked feature matrix",
            material_type="FEATURE_MATRIX",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "RFP_SECURITY", "OPERATIONS"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="client_demo_boundaries",
            title="Client-demo boundaries",
            material_type="DEMO_BOUNDARY",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["SALES", "PRE_SALES", "CLIENT_DEMO"],
            excluded_claims=blocked,
        ),
        CommercialMaterial(
            material_id="operator_demo_lead_checklist",
            title="Operator and demo-lead checklist",
            material_type="OPERATOR_CHECKLIST",
            source_ref=source_ref,
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "backend_proof_capture_repeatable",
                "client_ready_publication_blocked",
            ],
            allowed_audiences=["OPERATIONS", "PRE_SALES"],
            excluded_claims=blocked,
        ),
    ]
