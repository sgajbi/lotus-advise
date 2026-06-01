from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.bank_demo_proof.commercial_materials import (
    CommercialMaterial,
    CommercialMaterialPack,
    build_commercial_material_pack,
    validate_commercial_material_pack_against_register,
)
from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)
from src.core.bank_demo_proof.supported_claim_models import (
    SupportedClaim,
    SupportedClaimProofRequirement,
)
from src.core.bank_demo_proof.supported_claim_register import (
    build_default_supported_claim_register,
)


def _commercial_material(material_id: str = "demo_script") -> CommercialMaterial:
    return CommercialMaterial(
        material_id=material_id,
        title="Bank-demo script",
        material_type="DEMO_SCRIPT",
        source_ref="docs/commercial/RFC-0028-bank-demo-client-proof-materials.md#demo-script",
        mapped_claim_ids=["commercial_rfp_security_material_available"],
        allowed_audiences=["SALES", "PRE_SALES"],
        excluded_claims=["client_ready_publication"],
    )


def _commercial_material_pack(materials: list[CommercialMaterial]) -> CommercialMaterialPack:
    return CommercialMaterialPack(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
        required_claim_ids=["commercial_rfp_security_material_available"],
        blocked_claims=["client_ready_publication"],
        materials=materials,
    )


def test_commercial_material_pack_uses_bounded_business_safe_materials() -> None:
    pack = build_commercial_material_pack()

    assert pack.contract_name == "AdvisoryCommercialMaterialPack"
    assert "commercial_rfp_security_material_available" in pack.required_claim_ids
    assert "advisor_journey_product_surface_proven" in pack.required_claim_ids
    assert "advisor_journey_backend_evidence_available" not in pack.required_claim_ids
    assert all(
        set(pack.blocked_claims).issubset(material.excluded_claims) for material in pack.materials
    )
    assert (
        validate_commercial_material_pack_against_register(
            pack,
            build_default_supported_claim_register(),
        )
        is pack
    )


def test_commercial_material_pack_alignment_rejects_unknown_or_ui_pending_claims() -> None:
    register = build_default_supported_claim_register()
    ui_pending_claim = SupportedClaim(
        claim_id="partial_product_surface_pending",
        title="Partial product surface pending",
        classification="BACKEND_BACKED_UI_PENDING",
        audiences=["DEVELOPER", "PRE_SALES"],
        allowed_materials=["WIKI"],
        claim_text="The backend evidence exists, but product-surface proof is not complete.",
        evidence_refs=["proof.assets.sanitized_runtime_summary"],
        proof_requirements=[
            SupportedClaimProofRequirement(
                requirement_id="partial-product-surface-proof",
                evidence_ref="proof.assets.sanitized_runtime_summary",
            )
        ],
        wording_rules=["Use internal wording only."],
    )
    ui_pending_register = register.model_copy(
        update={"claims": [*register.claims, ui_pending_claim]}
    )

    unknown_pack = CommercialMaterialPack(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
        required_claim_ids=["unknown_claim"],
        blocked_claims=["client_ready_publication"],
        materials=[
            CommercialMaterial(
                material_id="unknown_claim_material",
                title="Unknown claim material",
                material_type="DEMO_SCRIPT",
                source_ref="docs/commercial/material.md",
                mapped_claim_ids=["unknown_claim"],
                allowed_audiences=["SALES"],
                excluded_claims=["client_ready_publication"],
            )
        ],
    )
    with pytest.raises(ValueError, match="unknown supported claims"):
        validate_commercial_material_pack_against_register(unknown_pack, register)

    ui_pending_pack = CommercialMaterialPack(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
        required_claim_ids=["partial_product_surface_pending"],
        blocked_claims=["client_ready_publication"],
        materials=[
            CommercialMaterial(
                material_id="ui_pending_material",
                title="UI pending material",
                material_type="DEMO_SCRIPT",
                source_ref="docs/commercial/material.md",
                mapped_claim_ids=["partial_product_surface_pending"],
                allowed_audiences=["SALES"],
                excluded_claims=["client_ready_publication"],
            )
        ],
    )
    with pytest.raises(ValueError, match="UI-pending claims"):
        validate_commercial_material_pack_against_register(ui_pending_pack, ui_pending_register)


def test_commercial_material_rejects_unsafe_source_refs_and_technical_copy() -> None:
    with pytest.raises(ValidationError, match="repository-local reference"):
        CommercialMaterial(
            material_id="unsafe_source",
            title="Unsafe source",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/material.md?token=should-not-leak",
            mapped_claim_ids=["commercial_rfp_security_material_available"],
            allowed_audiences=["SALES"],
            excluded_claims=["client_ready_publication"],
        )

    with pytest.raises(ValidationError, match="sensitive technical detail"):
        CommercialMaterial(
            material_id="unsafe_title",
            title="Raw prompt evidence",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/material.md",
            mapped_claim_ids=["commercial_rfp_security_material_available"],
            allowed_audiences=["SALES"],
            excluded_claims=["client_ready_publication"],
        )

    with pytest.raises(ValidationError, match="source_ref cannot contain sensitive material"):
        CommercialMaterial(
            material_id="unsafe_source_fragment",
            title="Unsafe source fragment",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/raw_prompt/material.md",
            mapped_claim_ids=["commercial_rfp_security_material_available"],
            allowed_audiences=["SALES"],
            excluded_claims=["client_ready_publication"],
        )

    with pytest.raises(ValidationError):
        CommercialMaterial(
            material_id="unsafe_audience",
            title="Unsafe audience",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/material.md",
            mapped_claim_ids=["commercial_rfp_security_material_available"],
            allowed_audiences=["ENGINEERING_DEBUG"],
            excluded_claims=["client_ready_publication"],
        )


def test_commercial_material_rejects_duplicate_claims_and_audiences() -> None:
    with pytest.raises(ValidationError, match="entries must be unique"):
        CommercialMaterial(
            material_id="duplicate_claims",
            title="Duplicate claims",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/material.md",
            mapped_claim_ids=[
                "commercial_rfp_security_material_available",
                "commercial_rfp_security_material_available",
            ],
            allowed_audiences=["SALES"],
            excluded_claims=["client_ready_publication"],
        )

    with pytest.raises(ValidationError, match="audiences must be unique"):
        CommercialMaterial(
            material_id="duplicate_audiences",
            title="Duplicate audiences",
            material_type="DEMO_SCRIPT",
            source_ref="docs/commercial/material.md",
            mapped_claim_ids=["commercial_rfp_security_material_available"],
            allowed_audiences=["SALES", "SALES"],
            excluded_claims=["client_ready_publication"],
        )


def test_commercial_material_pack_rejects_duplicate_material_ids() -> None:
    with pytest.raises(ValidationError, match="commercial material ids must be unique"):
        _commercial_material_pack(
            [
                _commercial_material("duplicate"),
                _commercial_material("duplicate"),
            ]
        )


def test_commercial_material_pack_requires_exact_blocked_claim_coverage() -> None:
    with pytest.raises(ValidationError, match="must exclude every blocked claim"):
        CommercialMaterialPack(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
            required_claim_ids=["commercial_rfp_security_material_available"],
            blocked_claims=["client_ready_publication", "external_client_communication"],
            materials=[_commercial_material()],
        )


def test_commercial_material_pack_requires_every_required_claim_to_be_mapped() -> None:
    with pytest.raises(ValidationError, match="required claims must all be mapped"):
        CommercialMaterialPack(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
            required_claim_ids=[
                "commercial_rfp_security_material_available",
                "backend_proof_capture_repeatable",
            ],
            blocked_claims=["client_ready_publication"],
            materials=[_commercial_material()],
        )

    with pytest.raises(ValidationError, match="required and blocked claims must be distinct"):
        CommercialMaterialPack(
            scenario_id=RFC28_CANONICAL_SCENARIO_ID,
            primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
            proof_marker=RFC28_CANONICAL_PROOF_MARKER,
            publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
            required_claim_ids=["commercial_rfp_security_material_available"],
            blocked_claims=["commercial_rfp_security_material_available"],
            materials=[_commercial_material()],
        )

    with pytest.raises(ValidationError, match="must exclude every blocked claim"):
        _commercial_material_pack(
            [
                CommercialMaterial(
                    material_id="substring_claim",
                    title="Substring claim",
                    material_type="DEMO_SCRIPT",
                    source_ref="docs/commercial/material.md",
                    mapped_claim_ids=["commercial_rfp_security_material_available"],
                    allowed_audiences=["SALES"],
                    excluded_claims=["not_client_ready_publication"],
                )
            ]
        )
