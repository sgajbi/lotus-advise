from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.bank_demo_proof.artifact_refs import normalize_local_artifact_ref
from src.core.bank_demo_proof.validation import (
    contains_sensitive_rfc28_term,
    normalize_lotus_advise_contract_ref,
)

SupportedClaimClassification = Literal[
    "IMPLEMENTATION_BACKED",
    "BACKEND_BACKED_UI_PENDING",
    "DEGRADED_SUPPORTED",
    "PLANNED_RFC",
    "UNSUPPORTED",
]
SupportedClaimAudience = Literal[
    "DEVELOPER",
    "BUSINESS_USER",
    "OPERATIONS",
    "SALES",
    "PRE_SALES",
    "CLIENT_DEMO",
    "RFP_SECURITY",
]
SupportedClaimMaterial = Literal[
    "README",
    "WIKI",
    "SUPPORTED_FEATURES",
    "DEMO_SCRIPT",
    "SCREENSHOT",
    "PRODUCT_ONE_PAGER",
    "RFP_RESPONSE",
    "SECURITY_PACK",
    "ARCHITECTURE_DECK",
    "ROI_STORY",
    "OPERATOR_RUNBOOK",
]
ProofAssetType = Literal[
    "API_RESPONSE_SUMMARY",
    "LIVE_VALIDATION_SUMMARY",
    "WORKBENCH_SCREENSHOT",
    "REPORT_PACKAGE_SUMMARY",
    "ARCHIVE_REFERENCE",
    "AI_LINEAGE_SUMMARY",
    "GOVERNANCE_INTEGRATION_SUMMARY",
    "SECURITY_CHECK_SUMMARY",
    "COMMERCIAL_DOCUMENT",
    "LOCAL_RUNTIME_BUNDLE",
]
ProofAssetAccessClass = Literal[
    "COMMIT_SAFE_SUMMARY",
    "CUSTOMER_CONSUMABLE_SUMMARY",
    "RESTRICTED_CUSTOMER_EVIDENCE",
    "OPERATOR_ONLY_DIAGNOSTICS",
    "LOCAL_ONLY_RUNTIME_EVIDENCE",
    "SECRET_MATERIAL",
]
ProofRetentionClass = Literal[
    "COMMIT_SOURCE",
    "LOCAL_EVIDENCE_BUNDLE",
    "ADVISORY_REVIEW_RECORD",
    "AUDIT_EVIDENCE",
    "DO_NOT_RETAIN",
]
ClientReadyProofPosture = Literal[
    "CLIENT_READY_REVIEW_REQUIRED",
    "CLIENT_READY_PUBLICATION_BLOCKED",
]

SUPPORTED_CLAIM_CLASSIFICATIONS: tuple[str, ...] = (
    "IMPLEMENTATION_BACKED",
    "BACKEND_BACKED_UI_PENDING",
    "DEGRADED_SUPPORTED",
    "PLANNED_RFC",
    "UNSUPPORTED",
)
RFC28_CANONICAL_SCENARIO_ID = "RFC28_BANK_DEMO_CLIENT_READY_PROOF_CANONICAL"
RFC28_CANONICAL_PROOF_MARKER = "BANK_DEMO_PROOF_PACK_CREATED"
RFC28_CANONICAL_PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"
_RFC28_IDENTIFIER_MAX_LENGTH = 160
_RFC28_BUSINESS_TITLE_MAX_LENGTH = 160
_RFC28_CLAIM_TEXT_MAX_LENGTH = 1000
_RFC28_ARTIFACT_URI_MAX_LENGTH = 512
_RFC28_CONTENT_HASH_MAX_LENGTH = 80
_RFC28_MAX_PROOF_ASSETS = 32
_RFC28_MAX_REPOSITORY_SHAS = 16
_RFC28_MAX_REF_LIST_ITEMS = 64
_RFC28_SHA256_HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_RFC28_COMMIT_ALLOWED_ACCESS_CLASSES = {
    "COMMIT_SAFE_SUMMARY",
    "CUSTOMER_CONSUMABLE_SUMMARY",
}


class DemoScenarioStep(BaseModel):
    step_id: str = Field(
        description="Stable scenario step identifier.",
        examples=["advisor_cockpit"],
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing scenario step title.",
        max_length=_RFC28_BUSINESS_TITLE_MAX_LENGTH,
    )
    owner_repository: str = Field(
        description="Repository that owns the step evidence.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    required_evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence references required before this step can be claimed.",
    )
    required_workbench_panels: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description=(
            "Workbench panel identifiers required when this step is a product-surface step."
        ),
    )

    @field_validator("step_id", "owner_repository")
    @classmethod
    def _step_identifiers_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="scenario step identifier is required")

    @field_validator("title")
    @classmethod
    def _step_title_must_be_business_safe(cls, value: str) -> str:
        normalized = _normalize_required_text(
            value,
            error_code="scenario step title is required",
        )
        if _contains_sensitive_technical_term(normalized):
            raise ValueError("scenario step title cannot contain sensitive technical detail")
        return normalized

    @field_validator("required_evidence_refs", "required_workbench_panels")
    @classmethod
    def _step_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="scenario step refs")


class AdvisoryDemoScenarioContract(BaseModel):
    contract_name: Literal["AdvisoryDemoScenarioContract"] = Field(
        default="AdvisoryDemoScenarioContract"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(
        description="Governed bank-demo scenario identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    governed_as_of_date: date = Field(description="Governed scenario as-of date.")
    proof_marker: str = Field(
        description="Evidence marker emitted by successful proof capture.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    required_evidence_markers: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence markers that must appear in a successful proof pack.",
    )
    required_source_products: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Active Advise data products used as source evidence.",
    )
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Capability boundaries that must not be overclaimed in the demo.",
    )
    steps: list[DemoScenarioStep] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Business scenario steps in demo order.",
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _scenario_identifiers_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="scenario identifier is required")

    @field_validator("required_evidence_markers", "required_source_products")
    @classmethod
    def _scenario_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="scenario refs")

    @field_validator("unsupported_boundaries")
    @classmethod
    def _scenario_boundaries_must_be_business_safe(cls, value: list[str]) -> list[str]:
        normalized = _normalize_ref_list(
            value,
            field_name="scenario unsupported_boundaries",
            max_item_length=_RFC28_CLAIM_TEXT_MAX_LENGTH,
        )
        for boundary in normalized:
            if _contains_sensitive_technical_term(boundary):
                raise ValueError("scenario unsupported boundary cannot contain sensitive detail")
        return normalized

    @model_validator(mode="after")
    def _proof_marker_must_be_required(self) -> AdvisoryDemoScenarioContract:
        if self.proof_marker not in self.required_evidence_markers:
            raise ValueError("proof_marker must be present in required_evidence_markers")
        step_ids = [step.step_id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("scenario step_id values must be unique")
        return self


class SupportedClaimProofRequirement(BaseModel):
    requirement_id: str = Field(
        description="Stable proof requirement identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    evidence_ref: str = Field(
        description="Evidence reference required for this claim.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    blocking: bool = Field(
        default=True,
        description="Whether missing evidence blocks claim promotion.",
    )


class SupportedClaim(BaseModel):
    claim_id: str = Field(
        description="Stable snake_case supported-claim identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    title: str = Field(
        description="Business-facing claim title.",
        max_length=_RFC28_BUSINESS_TITLE_MAX_LENGTH,
    )
    classification: SupportedClaimClassification = Field(
        description="Implementation-backed, degraded, planned, or unsupported claim posture."
    )
    audiences: list[SupportedClaimAudience] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Audiences allowed to consume this claim.",
    )
    allowed_materials: list[SupportedClaimMaterial] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Documentation or demo material where this claim may appear.",
    )
    claim_text: str = Field(
        description="Approved business-facing claim wording.",
        max_length=_RFC28_CLAIM_TEXT_MAX_LENGTH,
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Concrete implementation, validation, or proof references backing the claim.",
    )
    proof_requirements: list[SupportedClaimProofRequirement] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Proof requirements that must be satisfied before promotion.",
    )
    wording_rules: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Required wording guardrails for this claim.",
    )

    @field_validator("claim_id", "title", "claim_text")
    @classmethod
    def _claim_copy_must_be_business_safe(cls, value: str) -> str:
        normalized = _normalize_required_text(value, error_code="supported claim text is required")
        if _contains_sensitive_technical_term(normalized):
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
        return _normalize_ref_list(
            value,
            field_name="supported claim refs",
            max_item_length=_RFC28_CLAIM_TEXT_MAX_LENGTH,
        )

    @model_validator(mode="after")
    def _classification_matches_evidence_and_materials(self) -> SupportedClaim:
        if self.classification == "IMPLEMENTATION_BACKED" and (
            not self.evidence_refs or not self.proof_requirements
        ):
            raise ValueError("IMPLEMENTATION_BACKED claims require evidence and proof requirements")
        if self.classification in {"PLANNED_RFC", "UNSUPPORTED"}:
            forbidden_materials = {"SCREENSHOT", "PRODUCT_ONE_PAGER", "RFP_RESPONSE"}
            if forbidden_materials.intersection(self.allowed_materials):
                raise ValueError("PLANNED_RFC and UNSUPPORTED claims cannot be client-facing")
        if (
            self.classification == "BACKEND_BACKED_UI_PENDING"
            and "SCREENSHOT" in self.allowed_materials
        ):
            raise ValueError("BACKEND_BACKED_UI_PENDING claims cannot use screenshots")
        return self


def _normalize_required_text(value: str, *, error_code: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(error_code)
    return normalized


def _normalize_ref_list(
    value: list[str],
    *,
    field_name: str,
    max_item_length: int = _RFC28_IDENTIFIER_MAX_LENGTH,
) -> list[str]:
    normalized: list[str] = []
    for item in value:
        normalized_item = _normalize_required_text(
            str(item),
            error_code=f"{field_name} cannot contain blank entries",
        )
        if len(normalized_item) > max_item_length:
            raise ValueError(f"{field_name} entry is too long")
        if _contains_sensitive_technical_term(normalized_item):
            raise ValueError(f"{field_name} cannot contain sensitive technical detail")
        normalized.append(normalized_item)
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{field_name} entries must be unique")
    return normalized


def _contains_sensitive_technical_term(value: str) -> bool:
    return contains_sensitive_rfc28_term(value)


class ArtifactPolicy(BaseModel):
    commit_allowed_access_classes: list[ProofAssetAccessClass] = Field(
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Access classes allowed in committed proof summaries.",
    )
    local_only_access_classes: list[ProofAssetAccessClass] = Field(
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Access classes that must remain under output/ or equivalent local evidence.",
    )
    sensitive_material_rules: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
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
            normalized_rule = _normalize_required_text(
                rule,
                error_code="sensitive material rule is required",
            )
            if len(normalized_rule) > _RFC28_CLAIM_TEXT_MAX_LENGTH:
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
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio governed by the register.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    proof_marker: str = Field(
        description="Required proof marker for implementation-backed claims.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    claims: list[SupportedClaim] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Governed claim inventory.",
    )
    artifact_policy: ArtifactPolicy = Field(
        description="Commit/local/sensitive artifact handling policy."
    )

    @field_validator("scenario_id", "primary_portfolio_id", "proof_marker")
    @classmethod
    def _register_identifiers_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_text(
            value,
            error_code="supported-claim register identifier is required",
        )

    @model_validator(mode="after")
    def _claim_ids_must_be_unique(self) -> AdvisorySupportedClaimRegister:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError("claim_id values must be unique")
        return self


class ProofAsset(BaseModel):
    asset_id: str = Field(
        description="Stable proof asset identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    asset_type: ProofAssetType = Field(description="Proof asset family.")
    source_repository: str = Field(
        description="Repository that produced the asset.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    uri: str = Field(
        description="Relative committed or local output path for the asset.",
        max_length=_RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    access_class: ProofAssetAccessClass = Field(description="Access and sharing classification.")
    retention_class: ProofRetentionClass = Field(description="Retention posture for the asset.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Claims or proof requirements this asset supports.",
    )
    content_hash: str | None = Field(
        default=None,
        max_length=_RFC28_CONTENT_HASH_MAX_LENGTH,
        description="Optional stable hash for immutable or sanitized assets.",
    )
    commit_allowed: bool = Field(
        description="Whether this asset may be committed to the repository.",
    )

    @field_validator("asset_id", "source_repository")
    @classmethod
    def _asset_identifier_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="proof asset identifier is required")

    @field_validator("uri")
    @classmethod
    def _asset_uri_must_be_safe_local_ref(cls, value: str) -> str:
        normalized: str = normalize_local_artifact_ref(value, field_name="proof asset uri")
        return normalized

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="proof asset evidence_refs")

    @field_validator("content_hash")
    @classmethod
    def _content_hash_must_be_canonical_sha256(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not _RFC28_SHA256_HASH_PATTERN.fullmatch(normalized):
            raise ValueError("proof asset content_hash must be a canonical sha256 digest")
        return normalized

    @model_validator(mode="after")
    def _sensitive_assets_cannot_be_committed(self) -> ProofAsset:
        local_only_classes = {"LOCAL_ONLY_RUNTIME_EVIDENCE", "SECRET_MATERIAL"}
        if self.access_class in local_only_classes and self.commit_allowed:
            raise ValueError("local-only or secret proof assets cannot be commit_allowed")
        if self.access_class == "SECRET_MATERIAL" and self.retention_class != "DO_NOT_RETAIN":
            raise ValueError("secret proof assets must use DO_NOT_RETAIN")
        if self.commit_allowed:
            if self.access_class not in _RFC28_COMMIT_ALLOWED_ACCESS_CLASSES:
                raise ValueError("commit_allowed proof assets must use a commit-safe access class")
            if self.retention_class != "COMMIT_SOURCE":
                raise ValueError("commit_allowed proof assets must use COMMIT_SOURCE retention")
            if self.content_hash is None:
                raise ValueError("commit_allowed proof assets require a content_hash")
        return self


class AdvisoryBankDemoProofPack(BaseModel):
    contract_name: Literal["AdvisoryBankDemoProofPack"] = Field(default="AdvisoryBankDemoProofPack")
    contract_version: Literal["v1"] = Field(default="v1")
    proof_pack_id: str = Field(
        description="Stable proof-pack identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    scenario_id: str = Field(
        description="Governed demo scenario identifier.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    primary_portfolio_id: str = Field(
        description="Canonical portfolio proven by this pack.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    proof_marker: str = Field(
        description="Proof marker emitted by successful proof capture.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    generated_at: datetime = Field(description="UTC proof-pack generation timestamp.")
    correlation_id: str = Field(
        description="Correlation id for proof-pack generation.",
        max_length=_RFC28_IDENTIFIER_MAX_LENGTH,
    )
    client_ready_posture: ClientReadyProofPosture = Field(
        description="Client-ready publication posture proven by this pack."
    )
    repository_shas: dict[str, str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REPOSITORY_SHAS,
        description="Repository commit SHAs included in the proof pack.",
    )
    evidence_markers: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Evidence markers observed during proof capture.",
    )
    scenario_contract_ref: str = Field(
        description="Scenario contract reference.",
        max_length=_RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    supported_claim_register_ref: str = Field(
        description="Supported-claim register reference.",
        max_length=_RFC28_ARTIFACT_URI_MAX_LENGTH,
    )
    source_product_refs: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Active data products used as proof sources.",
    )
    assets: list[ProofAsset] = Field(
        max_length=_RFC28_MAX_PROOF_ASSETS,
        description="Proof asset index.",
    )
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        max_length=_RFC28_MAX_REF_LIST_ITEMS,
        description="Unsupported or blocked capabilities proven by the pack.",
    )

    @field_validator(
        "proof_pack_id",
        "scenario_id",
        "primary_portfolio_id",
        "proof_marker",
        "correlation_id",
    )
    @classmethod
    def _proof_pack_identifiers_must_be_bounded(cls, value: str) -> str:
        return _normalize_required_text(value, error_code="proof-pack identifier is required")

    @field_validator("scenario_contract_ref", "supported_claim_register_ref")
    @classmethod
    def _proof_pack_contract_refs_must_be_safe(cls, value: str) -> str:
        return normalize_lotus_advise_contract_ref(value, field_name="proof-pack contract ref")

    @field_validator("generated_at")
    @classmethod
    def _generated_at_must_be_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(None):
            raise ValueError("proof-pack generated_at must be timezone-aware UTC")
        return value

    @field_validator("repository_shas")
    @classmethod
    def _repository_shas_must_be_bounded(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for repository, sha in value.items():
            repository_name = _normalize_required_text(
                str(repository),
                error_code="repository name is required",
            )
            if len(repository_name) > _RFC28_IDENTIFIER_MAX_LENGTH:
                raise ValueError("repository name is too long")
            if _contains_sensitive_technical_term(repository_name):
                raise ValueError("repository name cannot contain sensitive technical detail")
            if repository_name in normalized:
                raise ValueError("repository names must be unique after normalization")
            repository_sha = _normalize_required_text(
                str(sha),
                error_code="repository sha is required",
            )
            if len(repository_sha) > _RFC28_IDENTIFIER_MAX_LENGTH:
                raise ValueError("repository sha is too long")
            if _contains_sensitive_technical_term(repository_sha):
                raise ValueError("repository sha cannot contain sensitive technical detail")
            normalized[repository_name] = repository_sha
        return normalized

    @field_validator("evidence_markers", "source_product_refs")
    @classmethod
    def _proof_pack_refs_must_be_bounded(cls, value: list[str]) -> list[str]:
        return _normalize_ref_list(value, field_name="proof-pack refs")

    @field_validator("unsupported_boundaries")
    @classmethod
    def _unsupported_boundaries_must_be_business_safe(cls, value: list[str]) -> list[str]:
        normalized = _normalize_ref_list(
            value,
            field_name="proof-pack unsupported_boundaries",
            max_item_length=_RFC28_CLAIM_TEXT_MAX_LENGTH,
        )
        for boundary in normalized:
            if _contains_sensitive_technical_term(boundary):
                raise ValueError("unsupported boundary cannot contain sensitive technical detail")
        return normalized

    @model_validator(mode="after")
    def _proof_pack_must_include_marker_and_block_unsafe_assets(self) -> AdvisoryBankDemoProofPack:
        if self.proof_marker not in self.evidence_markers:
            raise ValueError("proof_marker must be present in evidence_markers")
        asset_ids = [asset.asset_id for asset in self.assets]
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("proof-pack asset ids must be unique")
        return self
