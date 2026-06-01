from __future__ import annotations

from src.core.bank_demo_proof import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.supported_claim_register import (
    build_default_supported_claim_register,
)


def test_default_supported_claim_register_pins_canonical_claims() -> None:
    register = build_default_supported_claim_register()
    claim_postures = {claim.claim_id: claim.classification for claim in register.claims}

    assert register.scenario_id == RFC28_CANONICAL_SCENARIO_ID
    assert register.primary_portfolio_id == RFC28_CANONICAL_PORTFOLIO_ID
    assert register.proof_marker == RFC28_CANONICAL_PROOF_MARKER
    assert claim_postures == {
        "backend_proof_capture_repeatable": "IMPLEMENTATION_BACKED",
        "advisor_journey_backend_evidence_available": "BACKEND_BACKED_UI_PENDING",
        "advisor_journey_product_surface_proven": "IMPLEMENTATION_BACKED",
        "advisor_use_document_proof_available": "IMPLEMENTATION_BACKED",
        "degraded_runtime_boundary_evidence_available": "DEGRADED_SUPPORTED",
        "ai_policy_cockpit_proof_integrated": "IMPLEMENTATION_BACKED",
        "client_ready_publication_blocked": "UNSUPPORTED",
        "commercial_rfp_security_material_available": "IMPLEMENTATION_BACKED",
        "rfp_security_package_pending": "UNSUPPORTED",
    }

    for claim in register.claims:
        evidence_refs = set(claim.evidence_refs)
        for requirement in claim.proof_requirements:
            assert requirement.evidence_ref in evidence_refs, claim.claim_id


def test_default_supported_claim_register_keeps_ui_pending_claims_off_screenshots() -> None:
    register = build_default_supported_claim_register()

    for claim in register.claims:
        if claim.classification == "BACKEND_BACKED_UI_PENDING":
            assert "SCREENSHOT" not in claim.allowed_materials
            assert "CLIENT_DEMO" not in claim.audiences
            assert claim.proof_requirements

    product_surface_claim = next(
        claim
        for claim in register.claims
        if claim.claim_id == "advisor_journey_product_surface_proven"
    )
    assert product_surface_claim.classification == "IMPLEMENTATION_BACKED"
    assert {"PRODUCT_ONE_PAGER", "DEMO_SCRIPT", "ROI_STORY"}.issubset(
        product_surface_claim.allowed_materials
    )

    commercial_claim = next(
        claim
        for claim in register.claims
        if claim.claim_id == "commercial_rfp_security_material_available"
    )
    assert {"PRODUCT_ONE_PAGER", "RFP_RESPONSE", "SECURITY_PACK"}.issubset(
        commercial_claim.allowed_materials
    )
    assert "client-ready publication" in " ".join(commercial_claim.wording_rules)


def test_default_supported_claim_register_defines_artifact_policy_boundaries() -> None:
    policy = build_default_supported_claim_register().artifact_policy

    assert policy.commit_allowed_access_classes == [
        "COMMIT_SAFE_SUMMARY",
        "CUSTOMER_CONSUMABLE_SUMMARY",
    ]
    assert "SECRET_MATERIAL" in policy.local_only_access_classes
    assert "token" in policy.sensitive_material_rules[0].lower()
    assert "prompt" in policy.sensitive_material_rules[0].lower()


def test_default_supported_claim_register_uses_business_safe_wording() -> None:
    register = build_default_supported_claim_register()

    for claim in register.claims:
        combined = " ".join([claim.claim_text, *claim.wording_rules]).lower()
        assert "seam" not in combined
        assert "slice" not in combined
