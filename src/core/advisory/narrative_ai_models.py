from typing import Optional

from pydantic import BaseModel, Field

from src.core.advisory.narrative_types import ProposalNarrativeRequestedGenerationMode


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
