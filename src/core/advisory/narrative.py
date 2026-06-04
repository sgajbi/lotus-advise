from __future__ import annotations

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_ai import apply_ai_draft_sections
from src.core.advisory.narrative_ai_models import ProposalNarrativeAiLineage
from src.core.advisory.narrative_envelope_models import ProposalNarrative
from src.core.advisory.narrative_grounding import (
    TEMPLATE_POLICY_VERSION,
    build_proposal_narrative_grounding_packet,
)
from src.core.advisory.narrative_policy import (
    evaluate_proposal_narrative_guardrails,
    resolve_proposal_narrative_policy,
)
from src.core.advisory.narrative_request_models import ProposalNarrativeRequest
from src.core.advisory.narrative_sections import render_sections
from src.core.advisory.narrative_types import (
    ProposalNarrativeGenerationMode,
    ProposalNarrativeSectionKey,
)
from src.core.common.canonical import hash_canonical_payload
from src.integrations.lotus_ai.proposal_narrative import (
    generate_proposal_narrative_draft_with_lotus_ai,
)

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
    requested = request.sections or list(_ALL_SECTIONS)
    rendered = [section for section in render_sections(packet) if section.section_key in requested]
    ai_lineage: ProposalNarrativeAiLineage | None = None
    generation_mode: ProposalNarrativeGenerationMode = "DETERMINISTIC_TEMPLATE"
    if request.generation_mode == "AI_ASSISTED_DRAFT":
        rendered, ai_lineage, generation_mode = apply_ai_draft_sections(
            packet=packet,
            narrative_policy=narrative_policy,
            request=request,
            deterministic_sections=rendered,
            requested_sections=requested,
            generate_ai_draft=generate_proposal_narrative_draft_with_lotus_ai,
        )
    guardrail_results = evaluate_proposal_narrative_guardrails(rendered)
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
    narrative_id = hash_canonical_payload(payload).replace("sha256:", "pn_", 1)[:19]
    blocking_keys = {"risk_lens", "suitability"}
    if any(item.status == "FAIL" for item in guardrail_results):
        status = "BLOCKED_GUARDRAIL_FAILURE"
    elif narrative_policy.client_ready_blockers:
        status = "BLOCKED_POLICY_INCOMPLETE"
    elif any(item.evidence_key in blocking_keys for item in packet.missing_evidence):
        status = "BLOCKED_INSUFFICIENT_EVIDENCE"
    else:
        status = "READY_FOR_ADVISOR_REVIEW"
    return ProposalNarrative(
        narrative_id=narrative_id,
        status=status,
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
