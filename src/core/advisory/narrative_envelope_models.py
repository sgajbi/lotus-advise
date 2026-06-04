from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeMissingEvidence,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeDisclosure,
    ProposalNarrativeGuardrailResult,
    ProposalNarrativePolicy,
)
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_types import (
    ProposalNarrativeAudience,
    ProposalNarrativeGenerationMode,
    ProposalNarrativeReviewState,
    ProposalNarrativeStatus,
)


class ProposalNarrative(BaseModel):
    narrative_id: str = Field(
        description="Deterministic narrative identifier for this transient artifact narrative.",
        examples=["pn_abc12345"],
    )
    status: ProposalNarrativeStatus = Field(description="Narrative generation status.")
    audience: ProposalNarrativeAudience = Field(description="Narrative audience.")
    generation_mode: ProposalNarrativeGenerationMode = Field(
        default="DETERMINISTIC_TEMPLATE",
        description=(
            "Actual generation mode used for this narrative. AI-assisted output remains "
            "advisor-review draft output and is never client-ready."
        ),
    )
    review_state: ProposalNarrativeReviewState = Field(
        default="DRAFT",
        description="Review state for the advisor-review narrative projection.",
    )
    policy_version: str = Field(
        description="Narrative policy or template version used for deterministic rendering.",
        examples=["proposal-narrative-deterministic.v1"],
    )
    narrative_policy: ProposalNarrativePolicy = Field(
        description="Resolved narrative policy, disclosure selection, and promotion blockers."
    )
    ai_lineage: Optional[ProposalNarrativeAiLineage] = Field(
        default=None,
        description=(
            "AI adapter lineage or deterministic fallback evidence for AI-assisted requests."
        ),
    )
    grounding_packet: ProposalNarrativeGroundingPacket = Field(
        description="Grounding packet used by deterministic narrative rendering."
    )
    sections: List[ProposalNarrativeSection] = Field(
        default_factory=list,
        description="Ordered deterministic narrative sections.",
    )
    disclosures: List[ProposalNarrativeDisclosure] = Field(
        default_factory=list,
        description="Approved disclosures selected by deterministic narrative policy.",
    )
    guardrail_results: List[ProposalNarrativeGuardrailResult] = Field(
        default_factory=list,
        description="Deterministic unsupported-claim and source-reference guardrail results.",
    )
    limitations: List[ProposalNarrativeMissingEvidence] = Field(
        default_factory=list,
        description="Explicit limitations and missing evidence for this narrative.",
    )
