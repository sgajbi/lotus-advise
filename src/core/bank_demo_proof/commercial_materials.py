from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from src.core.bank_demo_proof.models import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
)

RFC28_COMMERCIAL_MATERIAL_REFS: tuple[str, ...] = (
    "docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
    "docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md#slice-10---commercial-rfp-security-architecture-roi-and-demo-package",
    "docs/demo/README.md#rfc-0028-bank-demo-proof-materials",
)


class CommercialMaterial(BaseModel):
    material_id: str = Field(description="Stable commercial material identifier.")
    title: str = Field(description="Business-facing material title.")
    material_type: Literal[
        "PRODUCT_ONE_PAGER",
        "RFP_RESPONSE",
        "SECURITY_PACK",
        "ARCHITECTURE_OUTLINE",
        "DEMO_SCRIPT",
        "PROOF_GUIDE",
        "ROI_STORY",
        "FEATURE_MATRIX",
        "DEMO_BOUNDARY",
        "OPERATOR_CHECKLIST",
    ] = Field(description="Governed material family.")
    source_ref: str = Field(description="Repository source reference for this material.")
    mapped_claim_ids: list[str] = Field(
        min_length=1,
        description="Supported-claim ids that govern the material wording.",
    )
    allowed_audiences: list[str] = Field(
        min_length=1,
        description="Audiences allowed to use the material.",
    )
    excluded_claims: list[str] = Field(
        default_factory=list,
        description="Unsupported claims explicitly excluded from the material.",
    )


class CommercialMaterialPack(BaseModel):
    contract_name: Literal["AdvisoryCommercialMaterialPack"] = Field(
        default="AdvisoryCommercialMaterialPack"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(description="Canonical RFC-0028 scenario id.")
    primary_portfolio_id: str = Field(description="Canonical proof portfolio id.")
    proof_marker: str = Field(description="Canonical proof marker required for the pack.")
    publication_posture: Literal["CUSTOMER_CONSUMABLE_WITH_BOUNDARIES"] = Field(
        description="Commercial publication posture for the material pack."
    )
    required_claim_ids: list[str] = Field(
        min_length=1,
        description="Supported-claim ids required before using the pack.",
    )
    blocked_claims: list[str] = Field(
        min_length=1,
        description="Claims that remain blocked in every commercial asset.",
    )
    materials: list[CommercialMaterial] = Field(
        min_length=1,
        description="Governed material inventory.",
    )

    @model_validator(mode="after")
    def _materials_must_map_to_required_claims(self) -> CommercialMaterialPack:
        required = set(self.required_claim_ids)
        for material in self.materials:
            if not set(material.mapped_claim_ids).issubset(required):
                raise ValueError("commercial material maps to an unsupported claim id")
            if "client_ready_publication" not in " ".join(material.excluded_claims):
                raise ValueError("commercial material must exclude client-ready publication")
        return self


def build_commercial_material_pack() -> CommercialMaterialPack:
    claim_ids = [
        "backend_proof_capture_repeatable",
        "advisor_journey_backend_evidence_available",
        "advisor_use_document_proof_available",
        "degraded_runtime_boundary_evidence_available",
        "ai_policy_cockpit_proof_integrated",
        "commercial_rfp_security_material_available",
        "client_ready_publication_blocked",
    ]
    blocked = [
        "client_ready_publication",
        "external_client_communication",
        "completed_policy_approval_or_sign_off",
        "legal_or_regulatory_advice",
        "bank_specific_security_attestation",
        "oms_order_fill_or_settlement",
    ]
    source_ref = RFC28_COMMERCIAL_MATERIAL_REFS[0]
    return CommercialMaterialPack(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
        required_claim_ids=claim_ids,
        blocked_claims=blocked,
        materials=[
            CommercialMaterial(
                material_id="product_one_pager",
                title="Private-banking advisory proof one-pager",
                material_type="PRODUCT_ONE_PAGER",
                source_ref=source_ref,
                mapped_claim_ids=[
                    "commercial_rfp_security_material_available",
                    "advisor_journey_backend_evidence_available",
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
                    "advisor_journey_backend_evidence_available",
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
        ],
    )
