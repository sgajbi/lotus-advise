from __future__ import annotations

from typing import Any, Literal

from src.core.advisory.artifact_models import ProposalArtifact
from src.core.advisory.narrative_grounding_models import (
    ProposalNarrativeGroundingPacket,
    ProposalNarrativeMissingEvidence,
    ProposalNarrativeSourceRef,
)
from src.core.advisory.narrative_policy import is_disclosure_policy_available
from src.core.advisory.narrative_request_models import (
    ProposalNarrativeRequest,
)
from src.core.common.canonical import hash_canonical_payload

TEMPLATE_POLICY_VERSION = "proposal-narrative-deterministic.v1"

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
            return str(takeaway.value)
    return None


def _risk_available(artifact: ProposalArtifact) -> bool:
    return str(artifact.risk_lens.status) == "AVAILABLE"


def _suitability_available(artifact: ProposalArtifact) -> bool:
    return str(artifact.suitability_summary.status) == "AVAILABLE"


def _facts_from_artifact(artifact: ProposalArtifact) -> dict[str, Any]:
    decision_summary = artifact.proposal_decision_summary
    alternatives = artifact.proposal_alternatives
    selected_alternative = None
    alternative_tradeoffs: list[str] = []
    alternative_improvements: list[str] = []
    alternative_deteriorations: list[str] = []
    if alternatives is not None:
        selected_alternative = next(
            (
                alternative
                for alternative in alternatives.alternatives
                if alternative.alternative_id == alternatives.selected_alternative_id
                or alternative.selected
            ),
            alternatives.alternatives[0] if alternatives.alternatives else None,
        )
        if selected_alternative is not None:
            alternative_tradeoffs = [
                tradeoff.summary for tradeoff in selected_alternative.advisor_tradeoffs[:3]
            ]
            if selected_alternative.comparison_summary is not None:
                alternative_tradeoffs.insert(
                    0, selected_alternative.comparison_summary.primary_tradeoff
                )
                alternative_improvements = selected_alternative.comparison_summary.improvements[:3]
                alternative_deteriorations = selected_alternative.comparison_summary.deteriorations[
                    :3
                ]
    approval_requirements = (
        decision_summary.approval_requirements if decision_summary is not None else []
    )
    material_changes = decision_summary.material_changes if decision_summary is not None else []
    missing_decision_evidence = (
        decision_summary.missing_evidence if decision_summary is not None else []
    )
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
        "primary_summary": decision_summary.primary_summary
        if decision_summary is not None
        else None,
        "decision_confidence": decision_summary.confidence
        if decision_summary is not None
        else None,
        "approval_requirement_count": len(approval_requirements),
        "blocking_approval_count": sum(
            1 for item in approval_requirements if item.blocking_until_approved
        ),
        "approval_requirement_summaries": [
            f"{item.approval_type}: {item.summary}"
            for item in approval_requirements[:3]
            if item.required
        ],
        "material_change_count": len(material_changes),
        "material_change_summaries": [item.summary for item in material_changes[:3]],
        "missing_decision_evidence_count": len(missing_decision_evidence),
        "missing_decision_evidence_summaries": [
            item.summary for item in missing_decision_evidence[:3]
        ],
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
        "selected_alternative_label": (
            selected_alternative.label if selected_alternative is not None else None
        ),
        "selected_alternative_objective": (
            selected_alternative.objective if selected_alternative is not None else None
        ),
        "selected_alternative_status": (
            selected_alternative.status if selected_alternative is not None else None
        ),
        "alternative_tradeoff_summaries": alternative_tradeoffs[:3],
        "alternative_improvement_summaries": alternative_improvements,
        "alternative_deterioration_summaries": alternative_deteriorations,
        "alternative_count": len(alternatives.alternatives) if alternatives is not None else 0,
        "rejected_alternative_count": (
            len(alternatives.rejected_candidates) if alternatives is not None else 0
        ),
        "rejected_alternative_summaries": (
            [item.summary for item in alternatives.rejected_candidates[:3]]
            if alternatives is not None
            else []
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


def _missing_evidence(
    artifact: ProposalArtifact, request: ProposalNarrativeRequest
) -> list[ProposalNarrativeMissingEvidence]:
    missing: list[ProposalNarrativeMissingEvidence] = [
        _missing(
            "mandate_policy",
            "client-ready narrative",
            (
                "Policy evaluation evidence is implemented, but completed mandate-policy "
                "approval/sign-off is not available for client-ready narrative publication."
            ),
        ),
        _missing(
            "review_workflow",
            "client-ready narrative",
            (
                "Advisor-review workflow is available; client-ready narrative publication "
                "remains blocked until explicit release authority is supported."
            ),
        ),
        _missing(
            "report_archive_lineage",
            "client-ready artifact inclusion",
            "Report/render/archive lineage is not available for this transient artifact narrative.",
        ),
    ]
    if not is_disclosure_policy_available(request.jurisdiction):
        missing.append(
            _missing(
                "disclosure_policy",
                "client-ready narrative",
                "Disclosure policy is unavailable for the requested narrative jurisdiction.",
            )
        )
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
    missing_evidence = _missing_evidence(artifact, request)
    payload = {
        "policy_version": TEMPLATE_POLICY_VERSION,
        "audience": request.audience,
        "artifact_id": artifact.artifact_id,
        "proposal_run_id": artifact.proposal_run_id,
        "facts": facts,
        "input_hashes": artifact.evidence_bundle.hashes.model_dump(mode="json"),
        "missing_evidence": [item.model_dump(mode="json") for item in missing_evidence],
    }
    packet_id = hash_canonical_payload(payload).replace("sha256:", "pgp_", 1)[:20]
    return ProposalNarrativeGroundingPacket(
        packet_id=packet_id,
        policy_version=TEMPLATE_POLICY_VERSION,
        audience=request.audience,
        source_refs=_source_refs(artifact),
        input_hashes=artifact.evidence_bundle.hashes.model_dump(mode="json"),
        facts=facts,
        missing_evidence=missing_evidence,
    )
