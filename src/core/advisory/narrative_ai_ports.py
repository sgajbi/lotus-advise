from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeAlias

from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_grounding_models import ProposalNarrativeGroundingPacket
from src.core.advisory.narrative_policy_models import ProposalNarrativePolicy
from src.core.advisory.narrative_types import ProposalNarrativeSectionKey

ADAPTER_VERSION = "proposal-narrative-lotus-ai-adapter.v1"
PROMPT_TEMPLATE_VERSION = "proposal-narrative-instructions.v1"
WORKFLOW_PACK_ID = "proposal_narrative_draft.pack"
WORKFLOW_PACK_VERSION = "v1"


class ProposalNarrativeDraftUnavailableError(Exception):
    authority = "lotus_ai"
    degraded_reason = "LOTUS_AI_NARRATIVE_UNAVAILABLE"


@dataclass(frozen=True)
class ProposalNarrativeDraftSection:
    section_key: ProposalNarrativeSectionKey
    title: str
    text: str


@dataclass(frozen=True)
class ProposalNarrativeDraftResponse:
    sections: tuple[ProposalNarrativeDraftSection, ...]
    lineage: ProposalNarrativeAiLineage


ProposalNarrativeDraftGenerator: TypeAlias = Callable[
    [
        ProposalNarrativeGroundingPacket,
        ProposalNarrativePolicy,
        list[ProposalNarrativeSectionKey],
        str | None,
    ],
    ProposalNarrativeDraftResponse,
]

_draft_generator: ProposalNarrativeDraftGenerator | None = None


def configure_proposal_narrative_draft_generator(
    generator: ProposalNarrativeDraftGenerator | None,
) -> None:
    global _draft_generator
    _draft_generator = generator


def get_proposal_narrative_draft_generator_for_tests() -> ProposalNarrativeDraftGenerator | None:
    return _draft_generator


def generate_proposal_narrative_draft(
    *,
    grounding_packet: ProposalNarrativeGroundingPacket,
    narrative_policy: ProposalNarrativePolicy,
    requested_sections: list[ProposalNarrativeSectionKey],
    requested_by: str | None,
) -> ProposalNarrativeDraftResponse:
    if _draft_generator is None:
        raise ProposalNarrativeDraftUnavailableError("LOTUS_AI_NARRATIVE_UNAVAILABLE")
    return _draft_generator(
        grounding_packet,
        narrative_policy,
        requested_sections,
        requested_by,
    )


def build_ai_fallback_lineage(reason: str) -> ProposalNarrativeAiLineage:
    return ProposalNarrativeAiLineage(
        requested_generation_mode="AI_ASSISTED_DRAFT",
        adapter_version=ADAPTER_VERSION,
        workflow_pack_id=WORKFLOW_PACK_ID,
        workflow_pack_version=WORKFLOW_PACK_VERSION,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
        model_version=None,
        workflow_run_id=None,
        fallback_reason=reason,
    )


__all__ = [
    "ProposalNarrativeDraftGenerator",
    "ProposalNarrativeDraftResponse",
    "ProposalNarrativeDraftSection",
    "ProposalNarrativeDraftUnavailableError",
    "build_ai_fallback_lineage",
    "configure_proposal_narrative_draft_generator",
    "generate_proposal_narrative_draft",
    "get_proposal_narrative_draft_generator_for_tests",
]
