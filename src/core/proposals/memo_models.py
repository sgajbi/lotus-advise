from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ProposalMemoSectionStatus = Literal["READY", "PENDING_REVIEW", "BLOCKED"]
ProposalMemoAudience = Literal[
    "ADVISOR",
    "COMPLIANCE",
    "INVESTMENT_DESK",
    "OPERATIONS",
    "AUDIT",
    "SALES_PRE_SALES",
    "CLIENT_DRAFT",
]

ProposalMemoSectionKey = Literal[
    "EXECUTIVE_SUMMARY",
    "CLIENT_AND_HOUSEHOLD_CONTEXT",
    "ADVISORY_OBJECTIVE_AND_CONSTRAINTS",
    "RECOMMENDATION",
    "REJECTED_ALTERNATIVES",
    "PORTFOLIO_IMPACT",
    "RISK_AND_SCENARIO_CONTEXT",
    "SUITABILITY_AND_BEST_INTEREST",
    "FEES_COSTS_TAX_AND_FRICTIONS",
    "CONFLICTS_AND_DISCLOSURES",
    "APPROVALS_CONSENTS_AND_MAKER_CHECKER",
    "REPORT_ARCHIVE_AND_DELIVERY_READINESS",
    "EXECUTION_HANDOFF_BOUNDARY",
    "EVIDENCE_AND_LINEAGE_APPENDIX",
    "COMPLIANCE_APPENDIX",
    "OPERATIONS_APPENDIX",
    "SUPPORTABILITY_APPENDIX",
]


class ProposalMemoMaterialClaim(BaseModel):
    claim_id: str = Field(description="Stable memo claim identifier.")
    text: str = Field(description="Business-readable claim text.")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Source evidence references supporting this material claim.",
    )
    source_authority_refs: list[str] = Field(
        default_factory=list,
        description="Source-authority families backing the claim.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Stable reason codes attached to the claim.",
    )


class ProposalMemoSection(BaseModel):
    section_id: ProposalMemoSectionKey = Field(description="Stable memo section identifier.")
    title: str = Field(description="Business-readable memo section title.")
    status: ProposalMemoSectionStatus = Field(description="Section readiness posture.")
    audience_visibility: list[ProposalMemoAudience] = Field(
        default_factory=list,
        description="Audiences allowed to see this section before future projection policy.",
    )
    summary: str = Field(description="Concise section summary.")
    material_claims: list[ProposalMemoMaterialClaim] = Field(
        default_factory=list,
        description="Evidence-backed material claims rendered by this section.",
    )
    claim_refs: list[str] = Field(
        default_factory=list,
        description="Stable claim identifiers included in this section.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references consumed by this section.",
    )
    source_authority_refs: list[str] = Field(
        default_factory=list,
        description="Source-authority families consumed by this section.",
    )
    missing_evidence: list[str] = Field(
        default_factory=list,
        description="Required evidence missing from source owners.",
    )
    degraded_evidence: list[str] = Field(
        default_factory=list,
        description="Available but incomplete, stale, or non-authoritative evidence.",
    )
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Stable reason codes explaining readiness and blockers.",
    )
    review_required: bool = Field(description="Whether human review is required.")
    owner_role: str = Field(description="Business owner role for this section.")
    last_material_input_hash: str = Field(
        description="Canonical hash of section input evidence before rendering."
    )
    section_hash: str = Field(description="Canonical hash of the rendered section payload.")


class ProposalMemoSourceAuthorityManifest(BaseModel):
    contract_version: str = Field(description="Source-readiness contract version.")
    overall_posture: str = Field(description="Overall source-readiness posture.")
    source_authority: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-owner section readiness grouped by source authority.",
    )
    section_statuses: dict[str, str] = Field(
        default_factory=dict,
        description="Source-readiness status by source section key.",
    )


class AdvisoryProposalMemoEvidencePack(BaseModel):
    memo_id: str = Field(description="Deterministic memo evidence-pack identifier.")
    memo_version: str = Field(description="Memo evidence-pack schema version.")
    proposal_id: str = Field(description="Proposal aggregate identifier.")
    proposal_version_no: int = Field(description="Immutable proposal version number.")
    proposal_version_id: str | None = Field(
        default=None,
        description="Immutable proposal version identifier when available.",
    )
    artifact_id: str | None = Field(default=None, description="Proposal artifact identifier.")
    status: ProposalMemoSectionStatus = Field(description="Overall memo readiness posture.")
    projection_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Current projection and publication policy for this memo.",
    )
    source_authority_manifest: ProposalMemoSourceAuthorityManifest = Field(
        description="Source authority and readiness manifest consumed by the memo builder."
    )
    sections: list[ProposalMemoSection] = Field(
        default_factory=list,
        description="Ordered advisor proposal memo sections.",
    )
    source_input_hash: str = Field(description="Canonical hash of memo input evidence.")
    memo_hash: str = Field(description="Canonical hash of the memo evidence pack.")
    supportability: dict[str, Any] = Field(
        default_factory=dict,
        description="Supportability and capability posture for this pure builder output.",
    )
