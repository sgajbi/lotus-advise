from __future__ import annotations

from typing import cast

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_ai import apply_ai_draft_sections
from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_ai_ports import generate_proposal_narrative_draft
from src.core.advisory.narrative_envelope_models import ProposalNarrative
from src.core.advisory.narrative_grounding import (
    TEMPLATE_POLICY_VERSION,
    build_proposal_narrative_grounding_packet,
)
from src.core.advisory.narrative_grounding_models import ProposalNarrativeGroundingPacket
from src.core.advisory.narrative_policy import (
    evaluate_proposal_narrative_guardrails,
    resolve_proposal_narrative_policy,
)
from src.core.advisory.narrative_policy_models import (
    ProposalNarrativeGuardrailResult,
    ProposalNarrativePolicy,
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_section_models import ProposalNarrativeSection
from src.core.advisory.narrative_sections import render_sections
from src.core.advisory.narrative_types import (
    ProposalNarrativeGenerationMode,
    ProposalNarrativeSectionKey,
)
from src.core.common.canonical import hash_canonical_payload

generate_proposal_narrative_draft_with_lotus_ai = generate_proposal_narrative_draft

_ALL_SECTIONS: tuple[ProposalNarrativeSectionKey, ...] = (
    "EXECUTIVE_SUMMARY",
    "RECOMMENDATION_RATIONALE",
    "RISK_AND_CONCENTRATION",
    "SUITABILITY_AND_MANDATE",
    "MATERIAL_CHANGES",
    "ALTERNATIVES_CONSIDERED",
    "APPROVALS_AND_NEXT_STEPS",
    "LIMITATIONS_AND_DISCLOSURES",
)


def build_deterministic_proposal_narrative(
    *,
    artifact: ProposalArtifact,
    request: ProposalNarrativeRequest,
) -> ProposalNarrative:
    packet = build_proposal_narrative_grounding_packet(artifact=artifact, request=request)
    narrative_policy = resolve_proposal_narrative_policy(artifact=artifact, request=request)
    requested = _requested_sections(request)
    rendered = _render_requested_sections(packet=packet, requested_sections=requested)
    rendered, ai_lineage, generation_mode = _apply_requested_generation_mode(
        packet=packet,
        narrative_policy=narrative_policy,
        request=request,
        rendered=rendered,
        requested_sections=requested,
    )
    guardrail_results = evaluate_proposal_narrative_guardrails(rendered)
    narrative_id = _narrative_id(
        packet=packet,
        request=request,
        generation_mode=generation_mode,
        ai_lineage=ai_lineage,
        narrative_policy=narrative_policy,
        guardrail_results=guardrail_results,
        rendered=rendered,
    )
    return ProposalNarrative(
        narrative_id=narrative_id,
        status=_narrative_status(
            packet=packet,
            narrative_policy=narrative_policy,
            guardrail_results=guardrail_results,
        ),
        audience=request.audience,
        generation_mode=generation_mode,
        policy_version=TEMPLATE_POLICY_VERSION,
        narrative_policy=narrative_policy,
        ai_lineage=ai_lineage,
        grounding_packet=packet,
        sections=rendered,
        disclosures=narrative_policy.required_disclosures,
        guardrail_results=guardrail_results,
        limitations=packet.missing_evidence,
    )


def _requested_sections(
    request: ProposalNarrativeRequest,
) -> list[ProposalNarrativeSectionKey]:
    return request.sections or list(_ALL_SECTIONS)


def _render_requested_sections(
    *,
    packet: ProposalNarrativeGroundingPacket,
    requested_sections: list[ProposalNarrativeSectionKey],
) -> list[ProposalNarrativeSection]:
    return [
        section for section in render_sections(packet) if section.section_key in requested_sections
    ]


def _apply_requested_generation_mode(
    *,
    packet: ProposalNarrativeGroundingPacket,
    narrative_policy: ProposalNarrativePolicy,
    request: ProposalNarrativeRequest,
    rendered: list[ProposalNarrativeSection],
    requested_sections: list[ProposalNarrativeSectionKey],
) -> tuple[
    list[ProposalNarrativeSection],
    ProposalNarrativeAiLineage | None,
    ProposalNarrativeGenerationMode,
]:
    if request.generation_mode != "AI_ASSISTED_DRAFT":
        return rendered, None, "DETERMINISTIC_TEMPLATE"
    return cast(
        tuple[
            list[ProposalNarrativeSection],
            ProposalNarrativeAiLineage,
            ProposalNarrativeGenerationMode,
        ],
        apply_ai_draft_sections(
            packet=packet,
            narrative_policy=narrative_policy,
            request=request,
            deterministic_sections=rendered,
            requested_sections=requested_sections,
            generate_ai_draft=generate_proposal_narrative_draft_with_lotus_ai,
        ),
    )


def _narrative_id(
    *,
    packet: ProposalNarrativeGroundingPacket,
    request: ProposalNarrativeRequest,
    generation_mode: ProposalNarrativeGenerationMode,
    ai_lineage: ProposalNarrativeAiLineage | None,
    narrative_policy: ProposalNarrativePolicy,
    guardrail_results: list[ProposalNarrativeGuardrailResult],
    rendered: list[ProposalNarrativeSection],
) -> str:
    payload = {
        "packet_id": packet.packet_id,
        "audience": request.audience,
        "generation_mode": generation_mode,
        "ai_lineage": ai_lineage.model_dump(mode="json") if ai_lineage is not None else None,
        "policy": narrative_policy.model_dump(mode="json"),
        "guardrail_results": [item.model_dump(mode="json") for item in guardrail_results],
        "sections": [section.model_dump(mode="json") for section in rendered],
        "input_hashes": packet.input_hashes,
    }
    return cast(str, hash_canonical_payload(payload).replace("sha256:", "pn_", 1)[:19])


def _narrative_status(
    *,
    packet: ProposalNarrativeGroundingPacket,
    narrative_policy: ProposalNarrativePolicy,
    guardrail_results: list[ProposalNarrativeGuardrailResult],
) -> str:
    if any(item.status == "FAIL" for item in guardrail_results):
        return "BLOCKED_GUARDRAIL_FAILURE"
    if narrative_policy.client_ready_blockers:
        return "BLOCKED_POLICY_INCOMPLETE"
    if _has_blocking_missing_evidence(packet):
        return "BLOCKED_INSUFFICIENT_EVIDENCE"
    return "READY_FOR_ADVISOR_REVIEW"


def _has_blocking_missing_evidence(packet: ProposalNarrativeGroundingPacket) -> bool:
    blocking_keys = {"risk_lens", "suitability"}
    return any(item.evidence_key in blocking_keys for item in packet.missing_evidence)
