from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    "CLIENT_READY_APPROVED",
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


class DemoScenarioStep(BaseModel):
    step_id: str = Field(
        description="Stable scenario step identifier.",
        examples=["advisor_cockpit"],
    )
    title: str = Field(description="Business-facing scenario step title.")
    owner_repository: str = Field(description="Repository that owns the step evidence.")
    required_evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references required before this step can be claimed.",
    )
    required_workbench_panels: list[str] = Field(
        default_factory=list,
        description=(
            "Workbench panel identifiers required when this step is a product-surface step."
        ),
    )


class AdvisoryDemoScenarioContract(BaseModel):
    contract_name: Literal["AdvisoryDemoScenarioContract"] = Field(
        default="AdvisoryDemoScenarioContract"
    )
    contract_version: Literal["v1"] = Field(default="v1")
    scenario_id: str = Field(description="Governed bank-demo scenario identifier.")
    primary_portfolio_id: str = Field(description="Canonical portfolio identifier.")
    governed_as_of_date: date = Field(description="Governed scenario as-of date.")
    proof_marker: str = Field(description="Evidence marker emitted by successful proof capture.")
    required_evidence_markers: list[str] = Field(
        min_length=1,
        description="Evidence markers that must appear in a successful proof pack.",
    )
    required_source_products: list[str] = Field(
        min_length=1,
        description="Active Advise data products used as source evidence.",
    )
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        description="Capability boundaries that must not be overclaimed in the demo.",
    )
    steps: list[DemoScenarioStep] = Field(
        min_length=1,
        description="Business scenario steps in demo order.",
    )

    @model_validator(mode="after")
    def _proof_marker_must_be_required(self) -> AdvisoryDemoScenarioContract:
        if self.proof_marker not in self.required_evidence_markers:
            raise ValueError("proof_marker must be present in required_evidence_markers")
        return self


class SupportedClaimProofRequirement(BaseModel):
    requirement_id: str = Field(description="Stable proof requirement identifier.")
    evidence_ref: str = Field(description="Evidence reference required for this claim.")
    blocking: bool = Field(
        default=True,
        description="Whether missing evidence blocks claim promotion.",
    )


class SupportedClaim(BaseModel):
    claim_id: str = Field(description="Stable snake_case supported-claim identifier.")
    title: str = Field(description="Business-facing claim title.")
    classification: SupportedClaimClassification = Field(
        description="Implementation-backed, degraded, planned, or unsupported claim posture."
    )
    audiences: list[SupportedClaimAudience] = Field(
        min_length=1,
        description="Audiences allowed to consume this claim.",
    )
    allowed_materials: list[SupportedClaimMaterial] = Field(
        default_factory=list,
        description="Documentation or demo material where this claim may appear.",
    )
    claim_text: str = Field(description="Approved business-facing claim wording.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Concrete implementation, validation, or proof references backing the claim.",
    )
    proof_requirements: list[SupportedClaimProofRequirement] = Field(
        default_factory=list,
        description="Proof requirements that must be satisfied before promotion.",
    )
    wording_rules: list[str] = Field(
        default_factory=list,
        description="Required wording guardrails for this claim.",
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


class ArtifactPolicy(BaseModel):
    commit_allowed_access_classes: list[ProofAssetAccessClass] = Field(
        description="Access classes allowed in committed proof summaries."
    )
    local_only_access_classes: list[ProofAssetAccessClass] = Field(
        description="Access classes that must remain under output/ or equivalent local evidence."
    )
    sensitive_material_rules: list[str] = Field(
        min_length=1,
        description="Rules for secrets, tokens, prompts, provider payloads, and raw runtime logs.",
    )

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
    scenario_id: str = Field(description="Scenario governed by this supported-claim register.")
    primary_portfolio_id: str = Field(description="Canonical portfolio governed by the register.")
    proof_marker: str = Field(description="Required proof marker for implementation-backed claims.")
    claims: list[SupportedClaim] = Field(min_length=1, description="Governed claim inventory.")
    artifact_policy: ArtifactPolicy = Field(
        description="Commit/local/sensitive artifact handling policy."
    )

    @model_validator(mode="after")
    def _claim_ids_must_be_unique(self) -> AdvisorySupportedClaimRegister:
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(set(claim_ids)) != len(claim_ids):
            raise ValueError("claim_id values must be unique")
        return self


class ProofAsset(BaseModel):
    asset_id: str = Field(description="Stable proof asset identifier.")
    asset_type: ProofAssetType = Field(description="Proof asset family.")
    source_repository: str = Field(description="Repository that produced the asset.")
    uri: str = Field(description="URI or local output path for the asset.")
    access_class: ProofAssetAccessClass = Field(description="Access and sharing classification.")
    retention_class: ProofRetentionClass = Field(description="Retention posture for the asset.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Claims or proof requirements this asset supports.",
    )
    content_hash: str | None = Field(
        default=None,
        description="Optional stable hash for immutable or sanitized assets.",
    )
    commit_allowed: bool = Field(
        description="Whether this asset may be committed to the repository.",
    )

    @model_validator(mode="after")
    def _sensitive_assets_cannot_be_committed(self) -> ProofAsset:
        local_only_classes = {"LOCAL_ONLY_RUNTIME_EVIDENCE", "SECRET_MATERIAL"}
        if self.access_class in local_only_classes and self.commit_allowed:
            raise ValueError("local-only or secret proof assets cannot be commit_allowed")
        if self.access_class == "SECRET_MATERIAL" and self.retention_class != "DO_NOT_RETAIN":
            raise ValueError("secret proof assets must use DO_NOT_RETAIN")
        return self


class AdvisoryBankDemoProofPack(BaseModel):
    contract_name: Literal["AdvisoryBankDemoProofPack"] = Field(default="AdvisoryBankDemoProofPack")
    contract_version: Literal["v1"] = Field(default="v1")
    proof_pack_id: str = Field(description="Stable proof-pack identifier.")
    scenario_id: str = Field(description="Governed demo scenario identifier.")
    primary_portfolio_id: str = Field(description="Canonical portfolio proven by this pack.")
    proof_marker: str = Field(description="Proof marker emitted by successful proof capture.")
    generated_at: datetime = Field(description="UTC proof-pack generation timestamp.")
    correlation_id: str = Field(description="Correlation id for proof-pack generation.")
    client_ready_posture: ClientReadyProofPosture = Field(
        description="Client-ready publication posture proven by this pack."
    )
    repository_shas: dict[str, str] = Field(
        min_length=1,
        description="Repository commit SHAs included in the proof pack.",
    )
    evidence_markers: list[str] = Field(
        min_length=1,
        description="Evidence markers observed during proof capture.",
    )
    scenario_contract_ref: str = Field(description="Scenario contract reference.")
    supported_claim_register_ref: str = Field(description="Supported-claim register reference.")
    source_product_refs: list[str] = Field(
        min_length=1,
        description="Active data products used as proof sources.",
    )
    assets: list[ProofAsset] = Field(description="Proof asset index.")
    unsupported_boundaries: list[str] = Field(
        min_length=1,
        description="Unsupported or blocked capabilities proven by the pack.",
    )

    @model_validator(mode="after")
    def _proof_pack_must_include_marker_and_block_unsafe_assets(self) -> AdvisoryBankDemoProofPack:
        if self.proof_marker not in self.evidence_markers:
            raise ValueError("proof_marker must be present in evidence_markers")
        if self.client_ready_posture == "CLIENT_READY_APPROVED":
            raise ValueError("CLIENT_READY_APPROVED is not supported before publication controls")
        return self
