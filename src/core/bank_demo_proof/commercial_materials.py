from __future__ import annotations

import re
from typing import Literal, cast
from urllib.parse import SplitResult, urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_CANONICAL_PORTFOLIO_ID,
    RFC28_CANONICAL_PROOF_MARKER,
    RFC28_CANONICAL_SCENARIO_ID,
    SupportedClaimAudience,
)
from src.core.bank_demo_proof.supported_claim_models import (
    AdvisorySupportedClaimRegister,
    SupportedClaim,
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
_CLIENT_FACING_MATERIAL_TYPES = {
    "PRODUCT_ONE_PAGER",
    "RFP_RESPONSE",
    "SECURITY_PACK",
    "DEMO_SCRIPT",
    "ROI_STORY",
    "FEATURE_MATRIX",
    "DEMO_BOUNDARY",
}
_CLIENT_FACING_BOUNDARY_CLAIM_IDS = {"client_ready_publication_blocked"}


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
        return cast(
            str,
            normalize_rfc28_business_text(
                value,
                field_name="commercial material field",
            ),
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
        return cast(
            str,
            normalize_rfc28_business_text(
                value,
                field_name="commercial material pack field",
            ),
        )

    @field_validator("required_claim_ids", "blocked_claims")
    @classmethod
    def _pack_claim_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="commercial material pack claim refs")

    @model_validator(mode="after")
    def _materials_must_map_to_required_claims(self) -> CommercialMaterialPack:
        required = set(self.required_claim_ids)
        blocked = set(self.blocked_claims)
        if required.intersection(blocked):
            raise ValueError("commercial material required and blocked claims must be distinct")
        material_ids = [material.material_id for material in self.materials]
        if len(set(material_ids)) != len(material_ids):
            raise ValueError("commercial material ids must be unique")
        mapped: set[str] = set()
        for material in self.materials:
            mapped_claims = set(material.mapped_claim_ids)
            if not mapped_claims.issubset(required):
                raise ValueError("commercial material maps to an unsupported claim id")
            mapped.update(mapped_claims)
            if not blocked.issubset(material.excluded_claims):
                raise ValueError("commercial material must exclude every blocked claim")
        if not required.issubset(mapped):
            raise ValueError("commercial material required claims must all be mapped")
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
    _validate_source_ref_text(normalized)
    parsed = urlsplit(normalized)
    _validate_source_ref_location(normalized, parsed)
    path = _normalized_source_ref_path(parsed.path)
    fragment = _normalized_source_ref_fragment(parsed.fragment)
    return urlunsplit(("", "", path, "", fragment))


def _validate_source_ref_text(normalized: str) -> None:
    if not normalized:
        raise ValueError("commercial material source_ref is required")
    if any(char in normalized for char in ("\r", "\n", "\t", "\x00")):
        raise ValueError("commercial material source_ref cannot contain control characters")


def _validate_source_ref_location(normalized: str, parsed: SplitResult) -> None:
    if parsed.scheme or parsed.netloc or parsed.query:
        raise ValueError("commercial material source_ref must be a repository-local reference")
    if normalized.startswith("/") or _RFC28_WINDOWS_DRIVE_REF.match(normalized):
        raise ValueError("commercial material source_ref must be relative, not absolute")


def _normalized_source_ref_path(path: str) -> str:
    path_parts = [part for part in path.split("/") if part]
    if any(part == ".." for part in path_parts):
        raise ValueError("commercial material source_ref cannot contain parent-directory traversal")
    if any(contains_sensitive_rfc28_term(part) for part in path_parts):
        raise ValueError("commercial material source_ref cannot contain sensitive material")
    return "/".join(path_parts)


def _normalized_source_ref_fragment(fragment: str) -> str:
    normalized_fragment = fragment.strip()
    if len(normalized_fragment) > _RFC28_MATERIAL_IDENTIFIER_MAX_LENGTH:
        raise ValueError("commercial material source_ref fragment is too long")
    if normalized_fragment and contains_sensitive_rfc28_term(normalized_fragment):
        raise ValueError(
            "commercial material source_ref fragment cannot contain sensitive material"
        )
    return normalized_fragment


def validate_commercial_material_pack_against_register(
    pack: CommercialMaterialPack,
    register: AdvisorySupportedClaimRegister,
) -> CommercialMaterialPack:
    claim_by_id = _registered_claims_by_id(register)
    _validate_all_referenced_claims_registered(
        _referenced_commercial_claim_ids(pack),
        claim_by_id,
    )
    for material in pack.materials:
        _validate_client_facing_material_claims(material, claim_by_id)
    return pack


def _registered_claims_by_id(
    register: AdvisorySupportedClaimRegister,
) -> dict[str, SupportedClaim]:
    return {claim.claim_id: claim for claim in register.claims}


def _referenced_commercial_claim_ids(pack: CommercialMaterialPack) -> set[str]:
    referenced_claim_ids = set(pack.required_claim_ids)
    for material in pack.materials:
        referenced_claim_ids.update(material.mapped_claim_ids)
    return referenced_claim_ids


def _validate_all_referenced_claims_registered(
    referenced_claim_ids: set[str],
    claim_by_id: dict[str, SupportedClaim],
) -> None:
    missing = sorted(referenced_claim_ids.difference(claim_by_id))
    if missing:
        raise ValueError(f"commercial material references unknown supported claims: {missing}")


def _validate_client_facing_material_claims(
    material: CommercialMaterial,
    claim_by_id: dict[str, SupportedClaim],
) -> None:
    if not _is_client_facing_material(material):
        return
    for claim_id in material.mapped_claim_ids:
        _validate_client_facing_claim_mapping(claim_id, claim_by_id[claim_id])


def _is_client_facing_material(material: CommercialMaterial) -> bool:
    return (
        "CLIENT_DEMO" in material.allowed_audiences
        or material.material_type in _CLIENT_FACING_MATERIAL_TYPES
    )


def _validate_client_facing_claim_mapping(claim_id: str, claim: SupportedClaim) -> None:
    if claim.classification in {"PLANNED_RFC", "UNSUPPORTED"} and (
        claim_id not in _CLIENT_FACING_BOUNDARY_CLAIM_IDS
    ):
        raise ValueError(
            "commercial material cannot map client-facing assets to planned or unsupported claims"
        )
    if claim.classification == "BACKEND_BACKED_UI_PENDING":
        raise ValueError("commercial material cannot map client-facing assets to UI-pending claims")


def build_commercial_material_pack() -> CommercialMaterialPack:
    from src.core.bank_demo_proof.commercial_material_catalog import (
        BLOCKED_COMMERCIAL_CLAIMS,
        REQUIRED_COMMERCIAL_CLAIM_IDS,
        build_commercial_materials,
    )

    source_ref = RFC28_COMMERCIAL_MATERIAL_REFS[0]
    return CommercialMaterialPack(
        scenario_id=RFC28_CANONICAL_SCENARIO_ID,
        primary_portfolio_id=RFC28_CANONICAL_PORTFOLIO_ID,
        proof_marker=RFC28_CANONICAL_PROOF_MARKER,
        publication_posture="CUSTOMER_CONSUMABLE_WITH_BOUNDARIES",
        required_claim_ids=REQUIRED_COMMERCIAL_CLAIM_IDS,
        blocked_claims=BLOCKED_COMMERCIAL_CLAIMS,
        materials=build_commercial_materials(source_ref),
    )
