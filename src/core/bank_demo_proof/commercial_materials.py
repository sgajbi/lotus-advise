from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    SupportedClaimAudience,
)
from src.core.bank_demo_proof.validation import (
    contains_sensitive_rfc28_term,
    normalize_required_rfc28_text,
    normalize_rfc28_business_text,
)

RFC28_COMMERCIAL_MATERIAL_REFS: tuple[str, ...] = (
    "docs/commercial/RFC-0028-bank-demo-client-proof-materials.md",
    "docs/rfcs/RFC-0028-bank-demo-journey-and-client-ready-proof.md#slice-10---commercial-rfp-security-architecture-roi-and-demo-package",
    "docs/demo/README.md#rfc-0028-bank-demo-proof-materials",
)
_RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH = 160
_RFC28_MATERIAL_TITLE_MAX_LENGTH = 160
_RFC28_MATERIAL_SOURCE_REF_MAX_LENGTH = 512
_RFC28_MATERIAL_LIST_MAX_ITEMS = 64
_RFC28_WINDOWS_DRIVE_REF = re.compile(r"^[A-Za-z]:")


class CommercialMaterial(BaseModel):
    material_id: str = Field(
        description="Stable commercial material identifier.",
        max_length=_RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing material title.",
        max_length=_RFC28_MATERIAL_TITLE_MAX_LENGTH,
    )
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
    source_ref: str = Field(
        description="Repository source reference for this material.",
        max_length=_RFC28_MATERIAL_SOURCE_REF_MAX_LENGTH,
    )
    mapped_claim_ids: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Supported-claim ids that govern the material wording.",
    )
    allowed_audiences: list[SupportedClaimAudience] = Field(
        min_length=1,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Audiences allowed to use the material.",
    )
    excluded_claims: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Unsupported claims explicitly excluded from the material.",
    )

    @field_validator("material_id", "title")
    @classmethod
    def _business_fields_must_be_safe(cls, value: str) -> str:
        return normalize_rfc28_business_text(
            value,
            field_name="commercial material field",
        )

    @field_validator("source_ref")
    @classmethod
    def _source_ref_must_be_repository_local(cls, value: str) -> str:
        return _normalize_repository_source_ref(value)

    @field_validator("mapped_claim_ids", "excluded_claims")
    @classmethod
    def _claim_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="commercial material claim refs")

    @field_validator("allowed_audiences")
    @classmethod
    def _audiences_must_be_unique(
        cls,
        value: list[SupportedClaimAudience],
    ) -> list[SupportedClaimAudience]:
        if len(set(value)) != len(value):
            raise ValueError("commercial material audiences must be unique")
        return value


class CommercialMaterialPack(BaseModel):
    contract_name: Literal["AdvisoryCommercialMaterialPack"] = Field(
        default="AdvisoryCommercialMaterialPack"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(
        description="Canonical RFC-0028 scenario id.",
        max_length=_RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical proof portfolio id.",
        max_length=_RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH,
    )
    proof_marker: str = Field(
        description="Canonical proof marker required for the pack.",
        max_length=_RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH,
    )
    publication_posture: Literal["CUSTOMER_CONSUMABLE_WITH_BOUNDARIES"] = Field(
        description="Commercial publication posture for the material pack."
    )
    required_claim_ids: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Supported-claim ids required before using the pack.",
    )
    blocked_claims: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Claims that remain blocked in every commercial asset.",
    )
    materials: list[CommercialMaterial] = Field(
        min_length=1,
        max_length=_RFC28_MATERIAL_LIST_MAX_ITEMS,
        description="Governed material inventory.",
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _pack_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_rfc28_business_text(
            value,
            field_name="commercial material pack field",
        )

    @field_validator("required_claim_ids", "blocked_claims")
    @classmethod
    def _pack_claim_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="commercial material pack claim refs")

    @model_validator(mode="after")
    def _materials_must_map_to_required_claims(self) -> CommercialMaterialPack:
        required = set(self.required_claim_ids)
        material_ids = [material.material_id for material in self.materials]
        if len(set(material_ids)) != len(material_ids):
            raise ValueError("commercial material ids must be unique")
        for material in self.materials:
            if not set(material.mapped_claim_ids).issubset(required):
                raise ValueError("commercial material maps to an unsupported claim id")
            if not set(self.blocked_claims).issubset(material.excluded_claims):
                raise ValueError("commercial material must exclude every blocked claim")
        return self


def _normalize_ref_list(value: list[str], *, field_name: str) -> list[str]:
    normalized: list[str] = []
    for item in value:
        normalized_item = normalize_required_rfc28_text(str(item), field_name=field_name)
        if len(normalized_item) > _RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH:
            raise ValueError(f"{field_name} entry is too long")
        if contains_sensitive_rfc28_term(normalized_item):
            raise ValueError(f"{field_name} cannot contain sensitive technical detail")
        normalized.append(normalized_item)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} entries must be unique")
    return normalized


def _normalize_repository_source_ref(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("commercial material source_ref is required")
    if any(char in normalized for char in ("\r", "\n", "\t", "\x00")):
        raise ValueError("commercial material source_ref cannot contain control characters")
    parsed = urlsplit(normalized)
    if parsed.scheme or parsed.netloc or parsed.query:
        raise ValueError("commercial material source_ref must be a repository-local reference")
    if normalized.startswith("/") or _RFC28_WINDOWS_DRIVE_REF.match(normalized):
        raise ValueError("commercial material source_ref must be relative, not absolute")
    path_parts = [part for part in parsed.path.split("/") if part]
    if any(part == ".." for part in path_parts):
        raise ValueError("commercial material source_ref cannot contain parent-directory traversal")
    if any(contains_sensitive_rfc28_term(part) for part in path_parts):
        raise ValueError("commercial material source_ref cannot contain sensitive material")
    fragment = parsed.fragment.strip()
    if len(fragment) > _RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH:
        raise ValueError("commercial material source_ref fragment is too long")
    if fragment and contains_sensitive_rfc28_term(fragment):
        raise ValueError(
            "commercial material source_ref fragment cannot contain sensitive material"
        )
    path = "/".join(path_parts)
    return urlunsplit(("", "", path, "", fragment))


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
