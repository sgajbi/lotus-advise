from typing import List, Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeMissingEvidence,
    ProposalNarrativeSourceRef,  # noqa: F401
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeDisclosure,
    ProposalNarrativeGuardrailResult,
    ProposalNarrativePolicy,
    ProposalNarrativePolicyContext,  # noqa: F401
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest  # noqa: F401
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_types import (
    ProposalNarrativeAudience,
    ProposalNarrativeClientAudience,  # noqa: F401
    ProposalNarrativeClientReadyStatus,
    ProposalNarrativeGenerationMode,
    ProposalNarrativeGuardrailStatus,  # noqa: F401
    ProposalNarrativePolicyStatus,  # noqa: F401
    ProposalNarrativeRequestedGenerationMode,
    ProposalNarrativeReviewAction,
    ProposalNarrativeReviewedState,
    ProposalNarrativeReviewState,
    ProposalNarrativeRiskPosture,  # noqa: F401
    ProposalNarrativeSectionKey,  # noqa: F401
    ProposalNarrativeStatus,
)


class ProposalNarrativeAiLineage(BaseModel):
    requested_generation_mode: ProposalNarrativeRequestedGenerationMode = Field(
        description="Generation mode requested by the caller.",
        examples=["AI_ASSISTED_DRAFT"],
    )
    adapter_version: str = Field(
        description="lotus-advise adapter version used for proposal narrative AI handoff.",
        examples=["proposal-narrative-lotus-ai-adapter.v1"],
    )
    workflow_pack_id: str = Field(
        description="lotus-ai workflow-pack identifier used for AI-assisted narrative generation.",
        examples=["proposal_narrative_draft.pack"],
    )
    workflow_pack_version: str = Field(
        description="lotus-ai workflow-pack version requested by the adapter.",
        examples=["v1"],
    )
    prompt_template_version: str = Field(
        description="Approved prompt/instruction template version used by the adapter.",
        examples=["proposal-narrative-instructions.v1"],
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Model version reported by lotus-ai, when available.",
        examples=["lotus-ai-governed-model.v1"],
    )
    workflow_run_id: Optional[str] = Field(
        default=None,
        description="lotus-ai workflow run identifier, when AI generation completed.",
        examples=["packrun_proposal_narrative_001"],
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Fallback reason when deterministic template output is returned instead.",
        examples=["LOTUS_AI_NARRATIVE_UNAVAILABLE"],
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


class ProposalNarrativeReviewRequest(BaseModel):
    action: ProposalNarrativeReviewAction = Field(
        description="Bounded review action for the persisted proposal narrative version.",
        examples=["APPROVE"],
    )
    reviewed_by: str = Field(
        description="Actor id recording the narrative review decision.",
        examples=["compliance_reviewer_001"],
    )
    reason: str = Field(
        description="Human-readable review rationale captured for audit.",
        examples=["Narrative is evidence-grounded and suitable for advisor use."],
    )
    client_ready_release_requested: bool = Field(
        default=False,
        description=(
            "Whether the reviewer requested client-ready release posture. Current RFC-0023 "
            "support records the request for audit but keeps client-ready release blocked until "
            "separately approved client-ready policy, disclosure, report/render/archive, and "
            "publication controls are implemented."
        ),
        examples=[False],
    )
    replacement_narrative_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional replacement narrative identifier when this review supersedes a prior draft."
        ),
        examples=["pn_replacement_001"],
    )


class ProposalNarrativeReviewRecord(BaseModel):
    review_id: str = Field(
        description="Review event identifier for this persisted narrative review.",
        examples=["pwe_narrative_review_001"],
    )
    proposal_id: str = Field(description="Proposal aggregate identifier.", examples=["pp_001"])
    proposal_version_no: int = Field(description="Reviewed immutable proposal version number.")
    narrative_id: str = Field(description="Reviewed narrative identifier.", examples=["pn_001"])
    action: ProposalNarrativeReviewAction = Field(
        description="Review action recorded.",
        examples=["APPROVE"],
    )
    review_state: ProposalNarrativeReviewedState = Field(
        description="Resulting narrative review state.",
        examples=["APPROVED_FOR_ADVISOR_USE"],
    )
    client_ready_status: ProposalNarrativeClientReadyStatus = Field(
        description="Client-ready release posture after this review action.",
        examples=["NOT_REQUESTED"],
    )
    reviewed_by: str = Field(
        description="Actor id that recorded the review.",
        examples=["compliance_reviewer_001"],
    )
    reviewed_at: str = Field(
        description="UTC ISO8601 review timestamp.",
        examples=["2026-05-22T08:30:00+00:00"],
    )
    reason: str = Field(
        description="Review rationale captured for audit.",
        examples=["Narrative is evidence-grounded and suitable for advisor use."],
    )
    source_narrative_hash: str = Field(
        description="Canonical hash of the reviewed narrative payload.",
        examples=["sha256:9c8a2f1d"],
    )
    replacement_narrative_id: Optional[str] = Field(
        default=None,
        description="Replacement narrative identifier requested by regeneration review, if any.",
        examples=["pn_replacement_001"],
    )
    replayed: bool = Field(
        default=False,
        description="Whether this response is an idempotent replay of an existing review event.",
        examples=[False],
    )
