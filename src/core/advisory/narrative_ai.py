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
    ProposalNarrativeDraftSection,
    build_ai_fallback_lineage,
    generate_proposal_narrative_draft_with_lotus_ai,
)

_AI_UNAVAILABLE_REASON = "LOTUS_AI_NARRATIVE_UNAVAILABLE"
_AiResponseResult = tuple[ProposalNarrativeDraftResponse | None, str | None]


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
    ai_response, fallback_reason = _generate_ai_response(
        packet=packet,
        narrative_policy=narrative_policy,
        request=request,
        requested_sections=requested_sections,
        generate_ai_draft=generate_ai_draft,
    )
    if ai_response is None:
        return _fallback_to_deterministic(
            deterministic_sections,
            fallback_reason or _AI_UNAVAILABLE_REASON,
        )

    ai_sections = _build_grounded_ai_sections(
        ai_response.sections,
        section_by_key=_index_sections_by_key(deterministic_sections),
    )
    if not ai_sections:
        return _fallback_to_deterministic(deterministic_sections, _AI_UNAVAILABLE_REASON)
    return ai_sections, ai_response.lineage, "AI_ASSISTED_DRAFT"


def _generate_ai_response(
    *,
    packet: ProposalNarrativeGroundingPacket,
    narrative_policy: ProposalNarrativePolicy,
    request: ProposalNarrativeRequest,
    requested_sections: list[ProposalNarrativeSectionKey],
    generate_ai_draft: Callable[..., ProposalNarrativeDraftResponse],
) -> _AiResponseResult:
    try:
        return (
            generate_ai_draft(
                grounding_packet=packet,
                narrative_policy=narrative_policy,
                requested_sections=requested_sections,
                requested_by=request.requested_by,
            ),
            None,
        )
    except LotusAIProposalNarrativeUnavailableError as exc:
        return None, str(exc)


def _index_sections_by_key(
    sections: list[ProposalNarrativeSection],
) -> dict[ProposalNarrativeSectionKey, ProposalNarrativeSection]:
    return {section.section_key: section for section in sections}


def _build_grounded_ai_sections(
    draft_sections: tuple[ProposalNarrativeDraftSection, ...],
    *,
    section_by_key: dict[ProposalNarrativeSectionKey, ProposalNarrativeSection],
) -> list[ProposalNarrativeSection]:
    return [
        _apply_ai_text_to_section(draft_section, source_section)
        for draft_section in draft_sections
        if (source_section := section_by_key.get(draft_section.section_key)) is not None
    ]


def _apply_ai_text_to_section(
    draft_section: ProposalNarrativeDraftSection,
    source_section: ProposalNarrativeSection,
) -> ProposalNarrativeSection:
    return ProposalNarrativeSection(
        section_key=draft_section.section_key,
        title=draft_section.title,
        text=draft_section.text,
        source_refs=source_section.source_refs,
        limitation_refs=source_section.limitation_refs,
    )


def _fallback_to_deterministic(
    deterministic_sections: list[ProposalNarrativeSection],
    reason: str,
) -> tuple[
    list[ProposalNarrativeSection],
    ProposalNarrativeAiLineage,
    ProposalNarrativeGenerationMode,
]:
    return (
        deterministic_sections,
        build_ai_fallback_lineage(reason),
        "DETERMINISTIC_TEMPLATE",
    )
