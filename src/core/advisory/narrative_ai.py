from __future__ import annotations

from collections.abc import Callable

from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_grounding_models import ProposalNarrativeGroundingPacket
from src.core.advisory.narrative_policy_models import ProposalNarrativePolicy
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_types import (
    ProposalNarrativeGenerationMode,
    ProposalNarrativeSectionKey,
)
from src.integrations.lotus_ai.proposal_narrative import (
    LotusAIProposalNarrativeUnavailableError,
    ProposalNarrativeDraftResponse,
    build_ai_fallback_lineage,
    generate_proposal_narrative_draft_with_lotus_ai,
)


def apply_ai_draft_sections(
    *,
    packet: ProposalNarrativeGroundingPacket,
    narrative_policy: ProposalNarrativePolicy,
    request: ProposalNarrativeRequest,
    deterministic_sections: list[ProposalNarrativeSection],
    requested_sections: list[ProposalNarrativeSectionKey],
    generate_ai_draft: Callable[
        ..., ProposalNarrativeDraftResponse
    ] = generate_proposal_narrative_draft_with_lotus_ai,
) -> tuple[
    list[ProposalNarrativeSection],
    ProposalNarrativeAiLineage,
    ProposalNarrativeGenerationMode,
]:
    section_by_key = {section.section_key: section for section in deterministic_sections}
    try:
        ai_response = generate_ai_draft(
            grounding_packet=packet,
            narrative_policy=narrative_policy,
            requested_sections=requested_sections,
            requested_by=request.requested_by,
        )
    except LotusAIProposalNarrativeUnavailableError as exc:
        return (
            deterministic_sections,
            build_ai_fallback_lineage(str(exc) or "LOTUS_AI_NARRATIVE_UNAVAILABLE"),
            "DETERMINISTIC_TEMPLATE",
        )

    ai_sections: list[ProposalNarrativeSection] = []
    for draft_section in ai_response.sections:
        source_section = section_by_key.get(draft_section.section_key)
        if source_section is None:
            continue
        ai_sections.append(
            ProposalNarrativeSection(
                section_key=draft_section.section_key,
                title=draft_section.title,
                text=draft_section.text,
                source_refs=source_section.source_refs,
                limitation_refs=source_section.limitation_refs,
            )
        )
    if not ai_sections:
        return (
            deterministic_sections,
            build_ai_fallback_lineage("LOTUS_AI_NARRATIVE_UNAVAILABLE"),
            "DETERMINISTIC_TEMPLATE",
        )
    return ai_sections, ai_response.lineage, "AI_ASSISTED_DRAFT"
