from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_types import (
    ProposalNarrativeAudience,
    ProposalNarrativeClientAudience,
    ProposalNarrativeRequestedGenerationMode,
    ProposalNarrativeSectionKey,
)


class ProposalNarrativeRequest(BaseModel):
    audience: ProposalNarrativeAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Narrative audience requested by the caller. Slice 5 supports advisor-review "
            "narrative only; client-draft and client-ready commentary remain gated."
        ),
        examples=["ADVISOR_REVIEW"],
    )
    sections: List[ProposalNarrativeSectionKey] = Field(
        default_factory=list,
        description=(
            "Optional ordered section allowlist. Empty means all deterministic advisor-review "
            "sections are returned in canonical order."
        ),
        examples=[["EXECUTIVE_SUMMARY", "RISK_AND_CONCENTRATION"]],
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Optional actor identifier requesting deterministic advisor-review narrative.",
        examples=["advisor_123"],
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description=(
            "Optional booking or client jurisdiction used for deterministic disclosure policy "
            "selection. Unsupported or missing jurisdictions block client-ready posture."
        ),
        examples=["SG"],
    )
    product_types: List[str] = Field(
        default_factory=list,
        description=(
            "Optional product-type hints used for disclosure policy selection. When omitted, "
            "Lotus derives product types from proposal evidence where possible."
        ),
        examples=[["EQUITY", "FX"]],
    )
    client_audience: ProposalNarrativeClientAudience = Field(
        default="ADVISOR_REVIEW",
        description=(
            "Policy audience used for disclosure and promotion gating. `CLIENT_READY` requests "
            "return blocked posture unless explicit client-ready release authority exists."
        ),
        examples=["ADVISOR_REVIEW"],
    )
    generation_mode: ProposalNarrativeRequestedGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description=(
            "Requested narrative generation mode. `AI_ASSISTED_DRAFT` uses the governed "
            "lotus-ai workflow-pack adapter and remains advisor-review draft output."
        ),
        examples=["DETERMINISTIC_TEMPLATE"],
    )
