from __future__ import annotations

from typing import Any, Literal

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_models import (
    ProposalNarrative,
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeMissingEvidence,
    ProposalNarrativeRequest,
    ProposalNarrativeSection,
    ProposalNarrativeSectionKey,
    ProposalNarrativeSourceRef,
)
from src.core.common.canonical import hash_canonical_payload

_POLICY_VERSION = "proposal-narrative-deterministic.v1"
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


ProposalNarrativeSourceRefType = Literal[
    "proposal_artifact",
    "proposal_result",
    "decision_summary",
    "risk_lens",
    "suitability",
    "alternatives",
    "limitations",
]
ProposalNarrativeMissingEvidenceKey = Literal[
    "risk_lens",
    "suitability",
    "alternatives",
    "mandate_policy",
    "disclosure_policy",
    "review_workflow",
    "report_archive_lineage",
]


def _source(
    ref_type: ProposalNarrativeSourceRefType, ref_id: str, field_path: str
) -> ProposalNarrativeSourceRef:
    return ProposalNarrativeSourceRef(ref_type=ref_type, ref_id=ref_id, field_path=field_path)


def _missing(
    evidence_key: ProposalNarrativeMissingEvidenceKey, required_for: str, message: str
) -> ProposalNarrativeMissingEvidence:
    return ProposalNarrativeMissingEvidence(
        evidence_key=evidence_key,
        required_for=required_for,
        message=message,
    )


def _top_takeaway(artifact: ProposalArtifact, code: str) -> str | None:
    for takeaway in artifact.summary.key_takeaways:
        if takeaway.code == code:
            return takeaway.value
    return None


def _risk_available(artifact: ProposalArtifact) -> bool:
    return artifact.risk_lens.status == "AVAILABLE"


def _suitability_available(artifact: ProposalArtifact) -> bool:
    return artifact.suitability_summary.status == "AVAILABLE"


def _facts_from_artifact(artifact: ProposalArtifact) -> dict[str, Any]:
    decision_summary = artifact.proposal_decision_summary
    alternatives = artifact.proposal_alternatives
    return {
        "proposal_status": artifact.status,
        "recommended_next_step": artifact.summary.recommended_next_step,
        "objective_tags": artifact.summary.objective_tags,
        "gate": artifact.gate_decision.gate,
        "gate_recommended_next_step": artifact.gate_decision.recommended_next_step,
        "decision_status": (
            decision_summary.decision_status if decision_summary is not None else None
        ),
        "primary_reason_code": (
            decision_summary.primary_reason_code if decision_summary is not None else None
        ),
        "recommended_next_action": (
            decision_summary.recommended_next_action if decision_summary is not None else None
        ),
        "material_change_count": (
            len(decision_summary.material_changes) if decision_summary is not None else 0
        ),
        "missing_decision_evidence_count": (
            len(decision_summary.missing_evidence) if decision_summary is not None else 0
        ),
        "risk_status": artifact.risk_lens.status,
        "risk_summary": artifact.risk_lens.summary,
        "risk_highlights": artifact.risk_lens.highlights,
        "suitability_status": artifact.suitability_summary.status,
        "suitability_new_issues": artifact.suitability_summary.new_issues,
        "suitability_resolved_issues": artifact.suitability_summary.resolved_issues,
        "suitability_persistent_issues": artifact.suitability_summary.persistent_issues,
        "highest_severity_new": artifact.suitability_summary.highest_severity_new,
        "alternatives_status": "AVAILABLE" if alternatives is not None else "NOT_AVAILABLE",
        "selected_alternative_id": (
            alternatives.selected_alternative_id if alternatives is not None else None
        ),
        "alternative_count": len(alternatives.alternatives) if alternatives is not None else 0,
        "rejected_alternative_count": (
            len(alternatives.rejected_candidates) if alternatives is not None else 0
        ),
        "trade_count": len(artifact.trades_and_funding.trade_list),
        "fx_count": len(artifact.trades_and_funding.fx_list),
        "cash_takeaway": _top_takeaway(artifact, "CASH"),
        "drift_takeaway": _top_takeaway(artifact, "DRIFT"),
        "risk_disclaimer": artifact.disclosures.risk_disclaimer,
        "costs_and_fees_note": artifact.assumptions_and_limits.costs_and_fees.notes,
        "tax_note": artifact.assumptions_and_limits.tax.notes,
        "execution_note": artifact.assumptions_and_limits.execution.notes,
    }


def _source_refs(artifact: ProposalArtifact) -> list[ProposalNarrativeSourceRef]:
    refs = [
        _source("proposal_artifact", artifact.artifact_id, "summary"),
        _source("proposal_artifact", artifact.artifact_id, "gate_decision"),
        _source("proposal_result", artifact.proposal_run_id, "status"),
        _source("limitations", artifact.artifact_id, "assumptions_and_limits"),
    ]
    if artifact.proposal_decision_summary is not None:
        refs.append(
            _source(
                "decision_summary",
                artifact.artifact_id,
                "proposal_decision_summary",
            )
        )
    if _risk_available(artifact):
        refs.append(_source("risk_lens", artifact.artifact_id, "risk_lens"))
    if _suitability_available(artifact):
        refs.append(_source("suitability", artifact.artifact_id, "suitability_summary"))
    if artifact.proposal_alternatives is not None:
        refs.append(_source("alternatives", artifact.artifact_id, "proposal_alternatives"))
    return refs


def _missing_evidence(artifact: ProposalArtifact) -> list[ProposalNarrativeMissingEvidence]:
    missing: list[ProposalNarrativeMissingEvidence] = [
        _missing(
            "mandate_policy",
            "client-ready narrative",
            "Mandate policy pack is not implemented for RFC-0023 Slice 5.",
        ),
        _missing(
            "disclosure_policy",
            "client-ready narrative",
            "Disclosure policy selection is deferred to RFC-0023 Slice 6.",
        ),
        _missing(
            "review_workflow",
            "client-ready narrative",
            "Narrative review workflow is deferred to later RFC-0023 slices.",
        ),
        _missing(
            "report_archive_lineage",
            "client-ready artifact inclusion",
            "Report/render/archive lineage is not available for Slice 5 narrative.",
        ),
    ]
    if not _risk_available(artifact):
        missing.append(
            _missing(
                "risk_lens",
                "risk narrative",
                "Concentration risk lens is unavailable for this proposal run.",
            )
        )
    if not _suitability_available(artifact):
        missing.append(
            _missing(
                "suitability",
                "suitability narrative",
                "Suitability scanner evidence is unavailable for this proposal run.",
            )
        )
    if artifact.proposal_alternatives is None:
        missing.append(
            _missing(
                "alternatives",
                "alternatives narrative",
                "Proposal alternatives were not requested or persisted for this proposal run.",
            )
        )
    return missing


def build_proposal_narrative_grounding_packet(
    *,
    artifact: ProposalArtifact,
    request: ProposalNarrativeRequest,
) -> ProposalNarrativeGroundingPacket:
    facts = _facts_from_artifact(artifact)
    payload = {
        "policy_version": _POLICY_VERSION,
        "audience": request.audience,
        "artifact_id": artifact.artifact_id,
        "proposal_run_id": artifact.proposal_run_id,
        "facts": facts,
        "input_hashes": artifact.evidence_bundle.hashes.model_dump(mode="json"),
        "missing_evidence": [item.model_dump(mode="json") for item in _missing_evidence(artifact)],
    }
    packet_id = hash_canonical_payload(payload).replace("sha256:", "pgp_", 1)[:20]
    return ProposalNarrativeGroundingPacket(
        packet_id=packet_id,
        policy_version=_POLICY_VERSION,
        audience=request.audience,
        source_refs=_source_refs(artifact),
        input_hashes=artifact.evidence_bundle.hashes.model_dump(mode="json"),
        facts=facts,
        missing_evidence=_missing_evidence(artifact),
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


def _render_sections(packet: ProposalNarrativeGroundingPacket) -> list[ProposalNarrativeSection]:
    facts = packet.facts
    sections = [
        _section(
            "EXECUTIVE_SUMMARY",
            "Executive Summary",
            (
                f"Proposal status is {facts['proposal_status']} with recommended next step "
                f"{facts['recommended_next_step']}. Decision status is "
                f"{facts['decision_status'] or 'UNAVAILABLE'}."
            ),
            _refs(packet, "proposal_artifact", "proposal_result", "decision_summary"),
        ),
        _section(
            "RECOMMENDATION_RATIONALE",
            "Recommendation Rationale",
            (
                f"The proposal is tagged for {', '.join(facts['objective_tags'])}. "
                f"It creates {facts['trade_count']} security trade(s) and {facts['fx_count']} "
                "FX intent(s), with recommendation reason "
                f"{facts['primary_reason_code'] or 'not available'}."
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
                f"{facts['suitability_persistent_issues']} persistent issue(s)."
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
                f"{facts['cash_takeaway'] or 'Cash impact is unavailable.'} "
                f"{facts['drift_takeaway'] or 'Reference-model drift evidence is unavailable.'}"
            ),
            _refs(packet, "proposal_artifact", "decision_summary"),
        ),
        _section(
            "ALTERNATIVES_CONSIDERED",
            "Alternatives Considered",
            (
                f"Alternatives evidence is available with {facts['alternative_count']} feasible "
                f"alternative(s), {facts['rejected_alternative_count']} rejected candidate(s), "
                f"and selected alternative {facts['selected_alternative_id'] or 'not selected'}."
                if facts["alternatives_status"] == "AVAILABLE"
                else (
                    "Proposal alternatives were not requested; no alternatives narrative is "
                    "asserted."
                )
            ),
            _refs(packet, "alternatives"),
            _limitations(packet, "alternatives"),
        ),
        _section(
            "APPROVALS_AND_NEXT_STEPS",
            "Approvals And Next Steps",
            (
                f"Workflow gate is {facts['gate']} with recommended action "
                f"{facts['gate_recommended_next_step']}."
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
    return sections


def build_deterministic_proposal_narrative(
    *,
    artifact: ProposalArtifact,
    request: ProposalNarrativeRequest,
) -> ProposalNarrative:
    packet = build_proposal_narrative_grounding_packet(artifact=artifact, request=request)
    requested = request.sections or list(_ALL_SECTIONS)
    rendered = [section for section in _render_sections(packet) if section.section_key in requested]
    payload = {
        "packet_id": packet.packet_id,
        "audience": request.audience,
        "sections": [section.model_dump(mode="json") for section in rendered],
        "input_hashes": packet.input_hashes,
    }
    narrative_id = hash_canonical_payload(payload).replace("sha256:", "pn_", 1)[:19]
    blocking_keys = {"risk_lens", "suitability"}
    status = (
        "BLOCKED_INSUFFICIENT_EVIDENCE"
        if any(item.evidence_key in blocking_keys for item in packet.missing_evidence)
        else "READY_FOR_ADVISOR_REVIEW"
    )
    return ProposalNarrative(
        narrative_id=narrative_id,
        status=status,
        audience=request.audience,
        policy_version=_POLICY_VERSION,
        grounding_packet=packet,
        sections=rendered,
        limitations=packet.missing_evidence,
    )
