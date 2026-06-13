from __future__ import annotations

from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeMissingEvidence,
    ProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_sections import render_sections


def test_render_sections_preserves_grounded_section_contract() -> None:
    packet = ProposalNarrativeGroundingPacket(
        packet_id="pgp_test",
        policy_version="proposal-narrative-deterministic.v1",
        audience="ADVISOR_REVIEW",
        source_refs=[
            ProposalNarrativeSourceRef(
                ref_type="proposal_artifact",
                ref_id="pa_1",
                field_path="proposal_artifact",
            ),
            ProposalNarrativeSourceRef(
                ref_type="decision_summary",
                ref_id="ds_1",
                field_path="proposal_decision_summary",
            ),
            ProposalNarrativeSourceRef(
                ref_type="risk_lens",
                ref_id="risk_1",
                field_path="risk_lens",
            ),
            ProposalNarrativeSourceRef(
                ref_type="limitations",
                ref_id="lim_1",
                field_path="limitations",
            ),
        ],
        facts={
            "proposal_status": "READY_FOR_REVIEW",
            "decision_status": "INSUFFICIENT_EVIDENCE",
            "primary_summary": "",
            "recommended_next_action": "REVIEW_RISK",
            "recommended_next_step": "Review risk evidence",
            "missing_decision_evidence_summaries": [
                "Risk lens is unavailable",
                "Suitability evidence is pending.",
            ],
            "approval_requirement_summaries": ["Compliance review required"],
            "objective_tags": ["REDUCE_CONCENTRATION"],
            "trade_count": 2,
            "fx_count": 1,
            "primary_reason_code": "MISSING_RISK_LENS",
            "decision_confidence": "MEDIUM",
            "risk_status": "UNAVAILABLE",
            "risk_summary": "Risk summary should not be asserted",
            "suitability_status": "AVAILABLE",
            "suitability_new_issues": 1,
            "suitability_resolved_issues": 2,
            "suitability_persistent_issues": 3,
            "material_change_count": 1,
            "material_change_summaries": ["Equity exposure falls"],
            "cash_takeaway": "",
            "drift_takeaway": "Drift remains inside tolerance.",
            "alternatives_status": "NOT_REQUESTED",
            "alternative_count": 0,
            "rejected_alternative_count": 0,
            "selected_alternative_label": "",
            "selected_alternative_id": "",
            "selected_alternative_objective": "",
            "selected_alternative_status": "",
            "alternative_tradeoff_summaries": [],
            "alternative_improvement_summaries": [],
            "alternative_deterioration_summaries": [],
            "rejected_alternative_summaries": [],
            "gate": "ADVISOR_REVIEW",
            "gate_recommended_next_step": "REVIEW_RISK",
            "approval_requirement_count": 1,
            "blocking_approval_count": 1,
            "risk_disclaimer": "Risk is source-dependent.",
            "costs_and_fees_note": "Costs are indicative.",
            "tax_note": "Tax is not advice.",
            "execution_note": "Execution remains outside Advise.",
        },
        missing_evidence=[
            ProposalNarrativeMissingEvidence(
                evidence_key="risk_lens",
                required_for="advisor review",
                message="Risk lens is unavailable.",
            ),
            ProposalNarrativeMissingEvidence(
                evidence_key="report_archive_lineage",
                required_for="advisor report",
                message="Report archive lineage is unavailable.",
            ),
        ],
    )

    sections = render_sections(packet)
    sections_by_key = {section.section_key: section for section in sections}

    assert [section.section_key for section in sections] == [
        "EXECUTIVE_SUMMARY",
        "RECOMMENDATION_RATIONALE",
        "RISK_AND_CONCENTRATION",
        "SUITABILITY_AND_MANDATE",
        "MATERIAL_CHANGES",
        "ALTERNATIVES_CONSIDERED",
        "APPROVALS_AND_NEXT_STEPS",
        "LIMITATIONS_AND_DISCLOSURES",
    ]
    assert sections_by_key["EXECUTIVE_SUMMARY"].source_refs[0].ref_id == "pa_1"
    assert "Evidence is insufficient" in sections_by_key["EXECUTIVE_SUMMARY"].text
    assert sections_by_key["RISK_AND_CONCENTRATION"].limitation_refs == ["risk_lens"]
    assert "cannot assert concentration impact" in sections_by_key["RISK_AND_CONCENTRATION"].text
    assert "not client-ready approval" in sections_by_key["SUITABILITY_AND_MANDATE"].text
    assert "Cash impact is unavailable" in sections_by_key["MATERIAL_CHANGES"].text
    assert "not requested" in sections_by_key["ALTERNATIVES_CONSIDERED"].text
    assert sections_by_key["LIMITATIONS_AND_DISCLOSURES"].limitation_refs == [
        "report_archive_lineage"
    ]


def test_render_sections_formats_available_alternatives_without_changing_sentence_policy() -> None:
    packet = ProposalNarrativeGroundingPacket(
        packet_id="pgp_alternatives",
        policy_version="proposal-narrative-deterministic.v1",
        audience="ADVISOR_REVIEW",
        source_refs=[
            ProposalNarrativeSourceRef(
                ref_type="alternatives",
                ref_id="alt_1",
                field_path="proposal_alternatives",
            )
        ],
        facts={
            "proposal_status": "READY_FOR_REVIEW",
            "decision_status": "READY_FOR_REVIEW",
            "primary_summary": "Proposal is ready for advisor review.",
            "recommended_next_action": "REVIEW_WITH_ADVISOR",
            "recommended_next_step": "Review with advisor",
            "missing_decision_evidence_summaries": [],
            "approval_requirement_summaries": [],
            "objective_tags": ["REDUCE_CONCENTRATION"],
            "trade_count": 1,
            "fx_count": 0,
            "primary_reason_code": "REDUCE_SINGLE_NAME_EXPOSURE",
            "decision_confidence": "HIGH",
            "risk_status": "AVAILABLE",
            "risk_summary": "Concentration risk falls.",
            "suitability_status": "AVAILABLE",
            "suitability_new_issues": 0,
            "suitability_resolved_issues": 1,
            "suitability_persistent_issues": 0,
            "material_change_count": 0,
            "material_change_summaries": [],
            "cash_takeaway": "Cash remains inside tolerance.",
            "drift_takeaway": "Drift remains inside tolerance.",
            "alternatives_status": "AVAILABLE",
            "alternative_count": 2,
            "rejected_alternative_count": 1,
            "selected_alternative_label": "Conservative trim",
            "selected_alternative_id": "alt_conservative",
            "selected_alternative_objective": "REDUCE_CONCENTRATION",
            "selected_alternative_status": "SELECTED",
            "alternative_tradeoff_summaries": ["Lower turnover", "Keeps mandate fit."],
            "alternative_improvement_summaries": ["Single-name exposure falls"],
            "alternative_deterioration_summaries": ["Expected cash drag increases."],
            "rejected_alternative_summaries": ["Aggressive trim breached cash band"],
            "gate": "ADVISOR_REVIEW",
            "gate_recommended_next_step": "REVIEW_WITH_ADVISOR",
            "approval_requirement_count": 0,
            "blocking_approval_count": 0,
            "risk_disclaimer": "Risk is source-dependent.",
            "costs_and_fees_note": "Costs are indicative.",
            "tax_note": "Tax is not advice.",
            "execution_note": "Execution remains outside Advise.",
        },
        missing_evidence=[],
    )

    sections = render_sections(packet)
    alternatives = {section.section_key: section for section in sections}["ALTERNATIVES_CONSIDERED"]

    assert alternatives.source_refs[0].ref_id == "alt_1"
    assert "2 feasible alternative(s) and 1 rejected candidate(s)" in alternatives.text
    assert "Selected alternative is Conservative trim" in alternatives.text
    assert "Tradeoff: Lower turnover. Keeps mandate fit." in alternatives.text
    assert "Improvement evidence: Single-name exposure falls." in alternatives.text
    assert "Deterioration evidence: Expected cash drag increases." in alternatives.text
    assert "Rejected-candidate evidence: Aggressive trim breached cash band." in alternatives.text
