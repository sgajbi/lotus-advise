from __future__ import annotations

from typing import Any

from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_section_models import (
    ProposalNarrativeSection,
)
from src.core.advisory.narrative_types import (
    ProposalNarrativeSectionKey,
)


def _refs(
    packet: ProposalNarrativeGroundingPacket, *ref_types: str
) -> list[ProposalNarrativeSourceRef]:
    return [ref for ref in packet.source_refs if ref.ref_type in ref_types]


def _limitations(packet: ProposalNarrativeGroundingPacket, *evidence_keys: str) -> list[str]:
    return [
        item.evidence_key for item in packet.missing_evidence if item.evidence_key in evidence_keys
    ]


def _section(
    key: ProposalNarrativeSectionKey,
    title: str,
    text: str,
    source_refs: list[ProposalNarrativeSourceRef],
    limitation_refs: list[str] | None = None,
) -> ProposalNarrativeSection:
    return ProposalNarrativeSection(
        section_key=key,
        title=title,
        text=text,
        source_refs=source_refs,
        limitation_refs=limitation_refs or [],
    )


def _sentence_list(items: list[str], fallback: str) -> str:
    cleaned = [item.strip() for item in items if item and item.strip()]
    if not cleaned:
        return fallback
    return " ".join(item if item.endswith(".") else f"{item}." for item in cleaned)


def _executive_summary_text(facts: dict[str, Any]) -> str:
    decision_status = facts["decision_status"] or "UNAVAILABLE"
    if facts["proposal_status"] == "BLOCKED" or decision_status == "BLOCKED_REMEDIATION_REQUIRED":
        return _blocked_executive_summary_text(facts)
    if decision_status == "INSUFFICIENT_EVIDENCE":
        return _insufficient_evidence_executive_summary_text(facts)
    return _ready_executive_summary_text(facts, decision_status=decision_status)


def _blocked_executive_summary_text(facts: dict[str, Any]) -> str:
    blocker_text = _sentence_list(
        facts["missing_decision_evidence_summaries"] or facts["approval_requirement_summaries"],
        facts["primary_summary"] or "Proposal cannot proceed until blockers are remediated.",
    )
    return (
        f"Blockers require attention before benefits are discussed. {blocker_text} "
        f"Recommended action is {facts['recommended_next_action'] or 'FIX_INPUT'}."
    )


def _insufficient_evidence_executive_summary_text(facts: dict[str, Any]) -> str:
    evidence_text = _sentence_list(
        facts["missing_decision_evidence_summaries"],
        facts["primary_summary"]
        or (
            "Required evidence is unavailable, so suitability and recommendation posture "
            "cannot be asserted."
        ),
    )
    return (
        f"Evidence is insufficient for a suitability pass or client-ready recommendation. "
        f"{evidence_text} Recommended action is "
        f"{facts['recommended_next_action'] or 'REVISE_PROPOSAL'}."
    )


def _ready_executive_summary_text(facts: dict[str, Any], *, decision_status: str) -> str:
    recommended_action = facts["recommended_next_action"] or facts["recommended_next_step"]
    return (
        f"Proposal status is {facts['proposal_status']} with decision status {decision_status}. "
        f"{facts['primary_summary'] or 'Decision summary evidence is available.'} "
        f"Recommended action is {recommended_action}."
    )


def _alternatives_text(facts: dict[str, Any]) -> str:
    if facts["alternatives_status"] != "AVAILABLE":
        return "Proposal alternatives were not requested; no alternatives narrative is asserted."
    selected = (
        facts["selected_alternative_label"] or facts["selected_alternative_id"] or "not selected"
    )
    tradeoffs = _sentence_list(
        facts["alternative_tradeoff_summaries"],
        "No selected-alternative tradeoff summary was persisted.",
    )
    improvements = _sentence_list(
        facts["alternative_improvement_summaries"],
        "No improvement over the baseline proposal was persisted.",
    )
    deteriorations = _sentence_list(
        facts["alternative_deterioration_summaries"],
        "No deterioration against the baseline proposal was persisted.",
    )
    rejected = _sentence_list(
        facts["rejected_alternative_summaries"],
        "No rejected-candidate explanation was persisted.",
    )
    return (
        f"Alternatives evidence includes {facts['alternative_count']} feasible alternative(s) "
        f"and {facts['rejected_alternative_count']} rejected candidate(s). Selected alternative "
        f"is {selected} for objective {facts['selected_alternative_objective'] or 'not available'} "
        f"with status {facts['selected_alternative_status'] or 'not available'}. "
        f"Tradeoff: {tradeoffs} Improvement evidence: {improvements} "
        f"Deterioration evidence: {deteriorations} Rejected-candidate evidence: {rejected}"
    )


def render_sections(packet: ProposalNarrativeGroundingPacket) -> list[ProposalNarrativeSection]:
    facts = packet.facts
    return [
        _executive_summary_section(packet, facts),
        _recommendation_rationale_section(packet, facts),
        _risk_and_concentration_section(packet, facts),
        _suitability_and_mandate_section(packet, facts),
        _material_changes_section(packet, facts),
        _alternatives_considered_section(packet, facts),
        _approvals_and_next_steps_section(packet, facts),
        _limitations_and_disclosures_section(packet, facts),
    ]


def _executive_summary_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "EXECUTIVE_SUMMARY",
        "Executive Summary",
        _executive_summary_text(facts),
        _refs(packet, "proposal_artifact", "proposal_result", "decision_summary"),
    )


def _recommendation_rationale_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "RECOMMENDATION_RATIONALE",
        "Recommendation Rationale",
        (
            f"The proposal is tagged for {', '.join(facts['objective_tags'])}. "
            f"It creates {facts['trade_count']} security trade(s) and {facts['fx_count']} "
            "FX intent(s). Decision reason is "
            f"{facts['primary_reason_code'] or 'not available'} "
            f"with confidence {facts['decision_confidence'] or 'not available'}."
        ),
        _refs(packet, "proposal_artifact", "decision_summary"),
    )


def _risk_and_concentration_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "RISK_AND_CONCENTRATION",
        "Risk And Concentration",
        _risk_and_concentration_text(facts),
        _refs(packet, "risk_lens"),
        _limitations(packet, "risk_lens"),
    )


def _risk_and_concentration_text(facts: dict[str, Any]) -> str:
    if facts["risk_status"] == "AVAILABLE":
        return str(facts["risk_summary"])
    return "Risk lens is unavailable; the narrative cannot assert concentration impact."


def _suitability_and_mandate_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "SUITABILITY_AND_MANDATE",
        "Suitability And Mandate",
        _suitability_and_mandate_text(facts),
        _refs(packet, "suitability"),
        _limitations(packet, "suitability", "mandate_policy"),
    )


def _suitability_and_mandate_text(facts: dict[str, Any]) -> str:
    if facts["suitability_status"] != "AVAILABLE":
        return "Suitability scanner evidence is unavailable; mandate fit cannot be asserted."
    return (
        "Suitability scanner evidence is available with "
        f"{facts['suitability_new_issues']} new, "
        f"{facts['suitability_resolved_issues']} resolved, and "
        f"{facts['suitability_persistent_issues']} persistent issue(s); "
        "this is evidence posture, not client-ready approval."
    )


def _material_changes_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "MATERIAL_CHANGES",
        "Material Changes",
        _material_changes_text(facts),
        _refs(packet, "proposal_artifact", "decision_summary"),
    )


def _material_changes_text(facts: dict[str, Any]) -> str:
    material_change_text = _sentence_list(
        facts["material_change_summaries"],
        "No material-change summary was persisted.",
    )
    return (
        f"{facts['material_change_count']} material change(s) were identified. "
        f"{material_change_text} "
        f"{facts['cash_takeaway'] or 'Cash impact is unavailable.'} "
        f"{facts['drift_takeaway'] or 'Reference-model drift evidence is unavailable.'}"
    )


def _alternatives_considered_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "ALTERNATIVES_CONSIDERED",
        "Alternatives Considered",
        _alternatives_text(facts),
        _refs(packet, "alternatives"),
        _limitations(packet, "alternatives"),
    )


def _approvals_and_next_steps_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "APPROVALS_AND_NEXT_STEPS",
        "Approvals And Next Steps",
        _approvals_and_next_steps_text(facts),
        _refs(packet, "proposal_artifact", "decision_summary"),
        _limitations(packet, "review_workflow"),
    )


def _approvals_and_next_steps_text(facts: dict[str, Any]) -> str:
    approval_summary_text = _sentence_list(
        facts["approval_requirement_summaries"],
        "No active approval requirement summary was persisted.",
    )
    return (
        f"Workflow gate is {facts['gate']} with recommended action "
        f"{facts['gate_recommended_next_step']}. Decision-summary action is "
        f"{facts['recommended_next_action'] or 'not available'}. "
        f"{facts['approval_requirement_count']} approval or remediation requirement(s) "
        "are active, including "
        f"{facts['blocking_approval_count']} blocking requirement(s). "
        f"{approval_summary_text}"
    )


def _limitations_and_disclosures_section(
    packet: ProposalNarrativeGroundingPacket,
    facts: dict[str, Any],
) -> ProposalNarrativeSection:
    return _section(
        "LIMITATIONS_AND_DISCLOSURES",
        "Limitations And Disclosures",
        _limitations_and_disclosures_text(facts),
        _refs(packet, "limitations"),
        _limitations(packet, "disclosure_policy", "report_archive_lineage"),
    )


def _limitations_and_disclosures_text(facts: dict[str, Any]) -> str:
    return (
        f"{facts['risk_disclaimer']} {facts['costs_and_fees_note']} "
        f"{facts['tax_note']} {facts['execution_note']}"
    )
