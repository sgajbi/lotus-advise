from typing import List

from pydantic import BaseModel, Field

from src.core.advisory.narrative_grounding_models import ProposalNarrativeSourceRef
from src.core.advisory.narrative_types import ProposalNarrativeSectionKey


class ProposalNarrativeSection(BaseModel):
    section_key: ProposalNarrativeSectionKey = Field(
        description="Canonical narrative section key.", examples=["EXECUTIVE_SUMMARY"]
    )
    title: str = Field(description="Advisor-facing section title.", examples=["Executive Summary"])
    text: str = Field(
        description="Deterministic narrative text derived only from grounding packet facts.",
        examples=["Proposal status is READY and requires client consent."],
    )
    source_refs: List[ProposalNarrativeSourceRef] = Field(
        default_factory=list,
        description="Source references used for this section.",
    )
    limitation_refs: List[str] = Field(
        default_factory=list,
        description="Missing evidence keys or limitations relevant to this section.",
    )
