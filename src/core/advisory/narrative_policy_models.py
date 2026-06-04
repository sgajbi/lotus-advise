from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_types import (
    ProposalNarrativeClientAudience,
    ProposalNarrativeGuardrailStatus,
    ProposalNarrativePolicyStatus,
    ProposalNarrativeRiskPosture,
    ProposalNarrativeSectionKey,
)


class ProposalNarrativePolicyContext(BaseModel):
    jurisdiction: str = Field(
        description="Resolved jurisdiction used by narrative policy.",
        examples=["SG"],
    )
    product_types: List[str] = Field(
        default_factory=list,
        description="Resolved product types used by disclosure policy.",
        examples=[["EQUITY", "FX"]],
    )
    risk_posture: ProposalNarrativeRiskPosture = Field(
        description="Resolved risk posture used by disclosure policy.",
        examples=["CONCENTRATION_REVIEW"],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        description="Policy audience used for promotion and disclosure gating.",
        examples=["ADVISOR_REVIEW"],
    )


class ProposalNarrativeDisclosure(BaseModel):
    disclosure_id: str = Field(
        description="Stable approved disclosure identifier.",
        examples=["DISC_SG_GENERAL_MARKET_RISK"],
    )
    jurisdiction: str = Field(description="Disclosure jurisdiction.", examples=["SG"])
    product_type: str = Field(description="Product type or posture the disclosure covers.")
    required_for: ProposalNarrativeClientAudience = Field(
        description="Audience for which this disclosure is required."
    )
    text: str = Field(description="Approved disclosure text selected by policy.")
    source_authority: str = Field(
        description="Policy authority that owns the disclosure text.",
        examples=["lotus-advise.rfc0023.slice6"],
    )
    policy_version: str = Field(
        description="Disclosure policy version that selected the disclosure.",
        examples=["advisory-narrative-policy.2026-05"],
    )


class ProposalNarrativeGuardrailResult(BaseModel):
    guardrail_id: str = Field(
        description="Stable guardrail identifier.",
        examples=["GR_UNSUPPORTED_GUARANTEE_CLAIM"],
    )
    status: ProposalNarrativeGuardrailStatus = Field(description="Guardrail evaluation status.")
    message: str = Field(description="Human-readable guardrail result.")
    section_key: Optional[ProposalNarrativeSectionKey] = Field(
        default=None,
        description="Section key that triggered the guardrail result, when applicable.",
    )


class ProposalNarrativePolicy(BaseModel):
    policy_version: str = Field(
        description="Narrative policy version used for disclosure and guardrail decisions.",
        examples=["advisory-narrative-policy.2026-05"],
    )
    status: ProposalNarrativePolicyStatus = Field(description="Policy readiness status.")
    context: ProposalNarrativePolicyContext = Field(
        description="Resolved policy context for the narrative."
    )
    required_disclosures: List[ProposalNarrativeDisclosure] = Field(
        default_factory=list,
        description="Approved disclosures selected by deterministic policy.",
    )
    client_ready_blockers: List[str] = Field(
        default_factory=list,
        description="Policy blockers preventing client-ready posture.",
    )
    prohibited_claims: List[str] = Field(
        default_factory=list,
        description="Unsupported claim patterns rejected by narrative guardrails.",
    )
