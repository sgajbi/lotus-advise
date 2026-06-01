from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.model_common import (
    RFC28_BUSINESS_TITLE_MAX_LENGTH,
    RFC28_CLAIM_TEXT_MAX_LENGTH,
    RFC28_IDENTIFIER_MAX_LENGTH,
    RFC28_MAX_REF_LIST_ITEMS,
    ProofAssetAccessClass,
    SupportedClaimAudience,
    SupportedClaimClassification,
    SupportedClaimMaterial,
    contains_sensitive_technical_term,
    normalize_ref_list,
    normalize_required_text,
)


class SupportedClaimProofRequirement(BaseModel):
    requirement_id: str = Field(
        description="Stable proof requirement identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    evidence_ref: str = Field(
        description="Evidence reference required for this claim.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    blocking: bool = Field(
        default=True,
        description="Whether missing evidence blocks claim promotion.",
    )


class SupportedClaim(BaseModel):
    claim_id: str = Field(
        description="Stable snake_case supported-claim identifier.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing claim title.",
        max_length=RFC28_BUSINESS_TITLE_MAX_LENGTH,
    )
    classification: SupportedClaimClassification = Field(
        description="Implementation-backed, degraded, planned, or unsupported claim posture."
    )
    audiences: list[SupportedClaimAudience] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Audiences allowed to consume this claim.",
    )
    allowed_materials: list[SupportedClaimMaterial] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Documentation or demo material where this claim may appear.",
    )
    claim_text: str = Field(
        description="Approved business-facing claim wording.",
        max_length=RFC28_CLAIM_TEXT_MAX_LENGTH,
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Concrete implementation, validation, or proof references backing the claim.",
    )
    proof_requirements: list[SupportedClaimProofRequirement] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Proof requirements that must be satisfied before promotion.",
    )
    wording_rules: list[str] = Field(
        default_factory=list,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Required wording guardrails for this claim.",
    )

    @field_validator("claim_id", "title", "claim_text")
    @classmethod
    def _claim_copy_must_be_business_safe(cls, value: str) -> str:
        normalized = normalize_required_text(value, error_code="supported claim text is required")
        if contains_sensitive_technical_term(normalized):
            raise ValueError("supported claim text cannot contain sensitive technical detail")
        return normalized

    @field_validator("audiences", "allowed_materials")
    @classmethod
    def _claim_taxonomy_lists_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("supported claim taxonomy lists must be unique")
        return value

    @field_validator("evidence_refs", "wording_rules")
    @classmethod
    def _claim_ref_lists_must_be_bounded(cls, value: list[str]) -> list[str]:
        return normalize_ref_list(
            value,
            field_name="supported claim refs",
            max_item_length=RFC28_CLAIM_TEXT_MAX_LENGTH,
        )

    @model_validator(mode="after")
    def _classification_matches_evidence_and_materials(self) -> SupportedClaim:
        if self.classification == "IMPLEMENTATION_BACKED" and (
            not self.evidence_refs or not self.proof_requirements
        ):
            raise ValueError("IMPLEMENTATION_BACKED claims require evidence and proof requirements")
        evidence_refs = set(self.evidence_refs)
        missing_requirement_refs = [
            requirement.evidence_ref
            for requirement in self.proof_requirements
            if requirement.evidence_ref not in evidence_refs
        ]
        if missing_requirement_refs:
            raise ValueError("supported claim proof requirements must use declared evidence refs")
        if self.classification in {"PLANNED_RFC", "UNSUPPORTED"}:
            forbidden_materials = {"SCREENSHOT", "PRODUCT_ONE_PAGER", "RFP_RESPONSE"}
            if forbidden_materials.intersection(self.allowed_materials):
                raise ValueError("PLANNED_RFC and UNSUPPORTED claims cannot be client-facing")
        if (
            self.classification == "BACKEND_BACKED_UI_PENDING"
            and "SCREENSHOT" in self.allowed_materials
        ):
            raise ValueError("BACKEND_BACKED_UI_PENDING claims cannot use screenshots")
        if self.classification == "BACKEND_BACKED_UI_PENDING":
            if "CLIENT_DEMO" in self.audiences:
                raise ValueError("BACKEND_BACKED_UI_PENDING claims cannot target client demos")
            forbidden_materials = {
                "PRODUCT_ONE_PAGER",
                "RFP_RESPONSE",
                "SECURITY_PACK",
            }
            if forbidden_materials.intersection(self.allowed_materials):
                raise ValueError(
                    "BACKEND_BACKED_UI_PENDING claims cannot use client-facing materials"
                )
        return self


class ArtifactPolicy(BaseModel):
    commit_allowed_access_classes: list[ProofAssetAccessClass] = Field(
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Access classes allowed in committed proof summaries.",
    )
    local_only_access_classes: list[ProofAssetAccessClass] = Field(
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Access classes that must remain under output/ or equivalent local evidence.",
    )
    sensitive_material_rules: list[str] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Rules for secrets, tokens, prompts, provider payloads, and raw runtime logs.",
    )

    @field_validator("commit_allowed_access_classes", "local_only_access_classes")
    @classmethod
    def _access_classes_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("artifact policy access classes must be unique")
        return value

    @field_validator("sensitive_material_rules")
    @classmethod
    def _sensitive_material_rules_must_be_bounded(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for rule in value:
            normalized_rule = normalize_required_text(
                rule,
                error_code="sensitive material rule is required",
            )
            if len(normalized_rule) > RFC28_CLAIM_TEXT_MAX_LENGTH:
                raise ValueError("sensitive material rule is too long")
            normalized.append(normalized_rule)
        if len(set(normalized)) != len(normalized):
            raise ValueError("sensitive material rules must be unique")
        return normalized

    @model_validator(mode="after")
    def _sensitive_rules_must_name_forbidden_materials(self) -> ArtifactPolicy:
        rule_text = " ".join(self.sensitive_material_rules).lower()
        if not all(term in rule_text for term in ("secret", "token", "prompt")):
            raise ValueError("sensitive_material_rules must cover secrets, tokens, and prompts")
        return self


class AdvisorySupportedClaimRegister(BaseModel):
    contract_name: Literal["AdvisorySupportedClaimRegister"] = Field(
        default="AdvisorySupportedClaimRegister"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(
        description="Scenario governed by this supported-claim register.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio governed by the register.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    proof_marker: str = Field(
        description="Required proof marker for implementation-backed claims.",
        max_length=RFC28_IDENTIFIER_MAX_LENGTH,
    )
    claims: list[SupportedClaim] = Field(
        min_length=1,
        max_length=RFC28_MAX_REF_LIST_ITEMS,
        description="Governed claim inventory.",
    )
    artifact_policy: ArtifactPolicy = Field(
        description="Commit/local/sensitive artifact handling policy."
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _register_identifiers_must_be_bounded(cls, value: str) -> str:
        return normalize_required_text(
            value,
            error_code="supported-claim register identifier is required",
        )

    @model_validator(mode="after")
    def _claim_ids_must_be_unique(self) -> AdvisorySupportedClaimRegister:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError("claim_id values must be unique")
        return self
