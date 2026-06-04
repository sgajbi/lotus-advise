from __future__ import annotations

from typing import Any

from src.core.advisory.narrative_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeSection,
    ProposalNarrativeSectionKey,
    ProposalNarrativeSourceRef,
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
        blocker_text = _sentence_list(
            facts["missing_decision_evidence_summaries"] or facts["approval_requirement_summaries"],
            facts["primary_summary"] or "Proposal cannot proceed until blockers are remediated.",
        )
        return (
            f"Blockers require attention before benefits are discussed. {blocker_text} "
            f"Recommended action is {facts['recommended_next_action'] or 'FIX_INPUT'}."
        )
    if decision_status == "INSUFFICIENT_EVIDENCE":
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
    material_change_text = _sentence_list(
        facts["material_change_summaries"],
        "No material-change summary was persisted.",
    )
    approval_summary_text = _sentence_list(
        facts["approval_requirement_summaries"],
        "No active approval requirement summary was persisted.",
    )
    return [
        _section(
            "EXECUTIVE_SUMMARY",
            "Executive Summary",
            _executive_summary_text(facts),
            _refs(packet, "proposal_artifact", "proposal_result", "decision_summary"),
        ),
        _section(
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
        ),
        _section(
            "RISK_AND_CONCENTRATION",
            "Risk And Concentration",
            (
                facts["risk_summary"]
                if facts["risk_status"] == "AVAILABLE"
                else "Risk lens is unavailable; the narrative cannot assert concentration impact."
            ),
            _refs(packet, "risk_lens"),
            _limitations(packet, "risk_lens"),
        ),
        _section(
            "SUITABILITY_AND_MANDATE",
            "Suitability And Mandate",
            (
                "Suitability scanner evidence is available with "
                f"{facts['suitability_new_issues']} new, "
                f"{facts['suitability_resolved_issues']} resolved, and "
                f"{facts['suitability_persistent_issues']} persistent issue(s); "
                "this is evidence posture, not client-ready approval."
                if facts["suitability_status"] == "AVAILABLE"
                else "Suitability scanner evidence is unavailable; mandate fit cannot be asserted."
            ),
            _refs(packet, "suitability"),
            _limitations(packet, "suitability", "mandate_policy"),
        ),
        _section(
            "MATERIAL_CHANGES",
            "Material Changes",
            (
                f"{facts['material_change_count']} material change(s) were identified. "
                f"{material_change_text} "
                f"{facts['cash_takeaway'] or 'Cash impact is unavailable.'} "
                f"{facts['drift_takeaway'] or 'Reference-model drift evidence is unavailable.'}"
            ),
            _refs(packet, "proposal_artifact", "decision_summary"),
        ),
        _section(
            "ALTERNATIVES_CONSIDERED",
            "Alternatives Considered",
            _alternatives_text(facts),
            _refs(packet, "alternatives"),
            _limitations(packet, "alternatives"),
        ),
        _section(
            "APPROVALS_AND_NEXT_STEPS",
            "Approvals And Next Steps",
            (
                f"Workflow gate is {facts['gate']} with recommended action "
                f"{facts['gate_recommended_next_step']}. Decision-summary action is "
                f"{facts['recommended_next_action'] or 'not available'}. "
                f"{facts['approval_requirement_count']} approval or remediation requirement(s) "
                "are active, including "
                f"{facts['blocking_approval_count']} blocking requirement(s). "
                f"{approval_summary_text}"
            ),
            _refs(packet, "proposal_artifact", "decision_summary"),
            _limitations(packet, "review_workflow"),
        ),
        _section(
            "LIMITATIONS_AND_DISCLOSURES",
            "Limitations And Disclosures",
            (
                f"{facts['risk_disclaimer']} {facts['costs_and_fees_note']} "
                f"{facts['tax_note']} {facts['execution_note']}"
            ),
            _refs(packet, "limitations"),
            _limitations(packet, "disclosure_policy", "report_archive_lineage"),
        ),
    ]
