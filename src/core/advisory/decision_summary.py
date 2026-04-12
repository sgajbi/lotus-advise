from src.core.advisory.decision_summary_models import (
    ProposalDecisionActionItem,
    ProposalDecisionApprovalRequirement,
    ProposalDecisionClientMandatePosture,
    ProposalDecisionConfidence,
    ProposalDecisionMissingEvidence,
    ProposalDecisionNextAction,
    ProposalDecisionRiskPosture,
    ProposalDecisionStatus,
    ProposalDecisionSuitabilityPosture,
    ProposalDecisionSummary,
)
from src.core.models import ProposalResult, SuitabilityResult

_DECISION_POLICY_VERSION = "advisory-decision-policy.2026-04"


def build_proposal_decision_summary(result: ProposalResult) -> ProposalDecisionSummary:
    missing_evidence = _build_missing_evidence(result)
    decision_status = _derive_decision_status(result, missing_evidence)
    approval_requirements = _build_approval_requirements(result, missing_evidence)
    primary_reason_code = _primary_reason_code(result, missing_evidence, decision_status)
    primary_summary = _primary_summary(decision_status, primary_reason_code)
    recommended_next_action = _recommended_next_action(decision_status, missing_evidence)
    confidence = _confidence(result, missing_evidence)
    evidence_refs = _build_evidence_refs(result, missing_evidence)
    advisor_action_items = _build_action_items(
        decision_status=decision_status,
        recommended_next_action=recommended_next_action,
        primary_reason_code=primary_reason_code,
        primary_summary=primary_summary,
        evidence_refs=evidence_refs,
    )

    return ProposalDecisionSummary(
        decision_status=decision_status,
        top_level_status=result.status,
        primary_reason_code=primary_reason_code,
        primary_summary=primary_summary,
        recommended_next_action=recommended_next_action,
        decision_policy_version=_DECISION_POLICY_VERSION,
        suitability_policy_version=(
            result.suitability.policy_version if result.suitability is not None else None
        ),
        confidence=confidence,
        approval_requirements=approval_requirements,
        material_changes=[],
        suitability_posture=_build_suitability_posture(result.suitability),
        missing_evidence=missing_evidence,
        risk_posture=_build_risk_posture(result),
        client_and_mandate_posture=ProposalDecisionClientMandatePosture(
            status="NOT_EVALUATED",
            summary=(
                "Client and mandate posture is not yet integrated into decision-summary policy."
            ),
        ),
        advisor_action_items=advisor_action_items,
        evidence_refs=evidence_refs,
    )


def _derive_decision_status(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> ProposalDecisionStatus:
    if result.status == "BLOCKED":
        return "BLOCKED_REMEDIATION_REQUIRED"

    blocking_missing_evidence = any(item.blocking for item in missing_evidence)
    if result.status == "PENDING_REVIEW" and blocking_missing_evidence:
        return "INSUFFICIENT_EVIDENCE"

    gate = result.gate_decision.gate if result.gate_decision is not None else None
    if gate == "COMPLIANCE_REVIEW_REQUIRED":
        return "REQUIRES_COMPLIANCE_REVIEW"
    if gate == "RISK_REVIEW_REQUIRED":
        return "REQUIRES_RISK_REVIEW"
    if gate == "CLIENT_CONSENT_REQUIRED":
        return "REQUIRES_CLIENT_CONSENT"

    if result.status == "PENDING_REVIEW":
        return "REVISION_RECOMMENDED"

    return "READY_FOR_CLIENT_REVIEW"


def _primary_reason_code(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
    decision_status: ProposalDecisionStatus,
) -> str:
    if decision_status == "INSUFFICIENT_EVIDENCE" and missing_evidence:
        return missing_evidence[0].reason_code
    if result.gate_decision is not None and result.gate_decision.reasons:
        return result.gate_decision.reasons[0].reason_code
    if missing_evidence:
        return missing_evidence[0].reason_code
    if decision_status == "READY_FOR_CLIENT_REVIEW":
        return "PROPOSAL_READY_FOR_CLIENT_REVIEW"
    if decision_status == "REVISION_RECOMMENDED":
        return "PROPOSAL_REVISION_RECOMMENDED"
    if decision_status == "REQUIRES_CLIENT_CONSENT":
        return "CLIENT_CONSENT_REQUIRED"
    if decision_status == "REQUIRES_RISK_REVIEW":
        return "RISK_REVIEW_REQUIRED"
    if decision_status == "REQUIRES_COMPLIANCE_REVIEW":
        return "COMPLIANCE_REVIEW_REQUIRED"
    if decision_status == "INSUFFICIENT_EVIDENCE":
        return "INSUFFICIENT_EVIDENCE"
    return "PROPOSAL_BLOCKED"


def _primary_summary(decision_status: ProposalDecisionStatus, primary_reason_code: str) -> str:
    if decision_status == "BLOCKED_REMEDIATION_REQUIRED":
        return "Proposal cannot proceed until blocking issues are remediated."
    if decision_status == "REQUIRES_COMPLIANCE_REVIEW":
        return "Proposal requires compliance review before client progression."
    if decision_status == "REQUIRES_RISK_REVIEW":
        return "Proposal requires risk review before client progression."
    if decision_status == "REQUIRES_CLIENT_CONSENT":
        return "Proposal is ready for client discussion and recorded client consent."
    if decision_status == "INSUFFICIENT_EVIDENCE":
        return "Proposal cannot be fully assessed because required evidence is unavailable."
    if decision_status == "REVISION_RECOMMENDED":
        return "Proposal should be revised before further progression."
    if primary_reason_code == "MISSING_RISK_LENS":
        return "Proposal is ready, but risk evidence is currently unavailable."
    return "Proposal is ready for client review."


def _recommended_next_action(
    decision_status: ProposalDecisionStatus,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> ProposalDecisionNextAction:
    if decision_status == "BLOCKED_REMEDIATION_REQUIRED":
        return "FIX_INPUT"
    if decision_status == "REQUIRES_COMPLIANCE_REVIEW":
        return "REVIEW_COMPLIANCE"
    if decision_status == "REQUIRES_RISK_REVIEW":
        return "REVIEW_RISK"
    if decision_status == "REQUIRES_CLIENT_CONSENT":
        return "DISCUSS_WITH_CLIENT"
    if decision_status == "INSUFFICIENT_EVIDENCE":
        for item in missing_evidence:
            if item.reason_code == "MISSING_CLIENT_CONTEXT":
                return "REQUEST_CLIENT_CONTEXT"
            if item.reason_code == "MISSING_MANDATE_CONTEXT":
                return "REQUEST_MANDATE_CONTEXT"
        return "REVISE_PROPOSAL"
    if decision_status == "REVISION_RECOMMENDED":
        return "REVISE_PROPOSAL"
    return "DISCUSS_WITH_CLIENT"


def _confidence(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> ProposalDecisionConfidence:
    if result.status == "BLOCKED" and missing_evidence:
        return "INSUFFICIENT"
    if missing_evidence:
        return "LOW"
    if result.status == "PENDING_REVIEW":
        return "MEDIUM"
    return "HIGH"


def _build_suitability_posture(
    suitability: SuitabilityResult | None,
) -> ProposalDecisionSuitabilityPosture | None:
    if suitability is None:
        return ProposalDecisionSuitabilityPosture(
            status="NOT_AVAILABLE",
            issue_count_new=0,
            issue_count_resolved=0,
            issue_count_persistent=0,
            highest_severity_new=None,
            recommended_gate=None,
        )
    return ProposalDecisionSuitabilityPosture(
        status="AVAILABLE",
        issue_count_new=suitability.summary.new_count,
        issue_count_resolved=suitability.summary.resolved_count,
        issue_count_persistent=suitability.summary.persistent_count,
        highest_severity_new=suitability.summary.highest_severity_new,
        recommended_gate=suitability.recommended_gate,
    )


def _build_risk_posture(result: ProposalResult) -> ProposalDecisionRiskPosture:
    risk_lens = result.explanation.get("risk_lens")
    authority_resolution = result.explanation.get("authority_resolution", {})
    if isinstance(risk_lens, dict):
        return ProposalDecisionRiskPosture(
            status="AVAILABLE",
            source_service=_string_or_none(risk_lens.get("source_service")),
            summary="Risk lens evidence is available from canonical upstream enrichment.",
        )
    if authority_resolution.get("risk_authority") == "unavailable":
        return ProposalDecisionRiskPosture(
            status="UNAVAILABLE",
            source_service=None,
            summary="Risk lens evidence is unavailable for this proposal run.",
        )
    return ProposalDecisionRiskPosture(
        status="UNAVAILABLE",
        source_service=None,
        summary="Risk lens evidence was not attached to this proposal result.",
    )


def _build_missing_evidence(result: ProposalResult) -> list[ProposalDecisionMissingEvidence]:
    items: list[ProposalDecisionMissingEvidence] = []
    data_quality = result.diagnostics.data_quality
    if data_quality.get("price_missing"):
        items.append(
            ProposalDecisionMissingEvidence(
                evidence_type="MARKET_PRICE",
                reason_code="MISSING_REQUIRED_MARKET_PRICE",
                summary="Required price data is missing for one or more instruments.",
                blocking=result.status == "BLOCKED",
                evidence_refs=["proposal.diagnostics.data_quality.price_missing"],
            )
        )
    if data_quality.get("fx_missing"):
        items.append(
            ProposalDecisionMissingEvidence(
                evidence_type="FX_RATE",
                reason_code="MISSING_REQUIRED_FX_DATA",
                summary="Required FX data is missing for one or more currency pairs.",
                blocking=result.status == "BLOCKED",
                evidence_refs=["proposal.diagnostics.data_quality.fx_missing"],
            )
        )
    authority_resolution = result.explanation.get("authority_resolution", {})
    if authority_resolution.get("risk_authority") == "unavailable":
        items.append(
            ProposalDecisionMissingEvidence(
                evidence_type="RISK_LENS",
                reason_code="MISSING_RISK_LENS",
                summary="Canonical risk evidence is unavailable for this proposal run.",
                blocking=result.status != "READY",
                evidence_refs=["proposal.explanation.authority_resolution"],
            )
        )
    if result.suitability is not None:
        for issue in result.suitability.issues:
            if issue.dimension == "DATA_QUALITY":
                items.append(
                    ProposalDecisionMissingEvidence(
                        evidence_type="SUITABILITY_DATA_QUALITY",
                        reason_code=issue.issue_id,
                        summary=issue.summary,
                        blocking=result.status == "BLOCKED" and issue.severity == "HIGH",
                        evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
                    )
                )
                continue
            if issue.classification != "UNKNOWN_DUE_TO_MISSING_EVIDENCE":
                continue
            items.append(
                ProposalDecisionMissingEvidence(
                    evidence_type="SUITABILITY_CONTEXT",
                    reason_code=issue.issue_id,
                    summary=issue.summary,
                    blocking=result.status != "READY",
                    evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
                )
            )
    return items


def _build_approval_requirements(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[ProposalDecisionApprovalRequirement]:
    requirements: list[ProposalDecisionApprovalRequirement] = []
    gate = result.gate_decision.gate if result.gate_decision is not None else None
    if gate == "COMPLIANCE_REVIEW_REQUIRED":
        requirements.append(
            ProposalDecisionApprovalRequirement(
                approval_type="COMPLIANCE_REVIEW",
                required=True,
                severity="HIGH",
                reason_code="COMPLIANCE_REVIEW_REQUIRED",
                summary="Compliance review is required before client progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=_DECISION_POLICY_VERSION,
            )
        )
    if gate == "RISK_REVIEW_REQUIRED":
        requirements.append(
            ProposalDecisionApprovalRequirement(
                approval_type="RISK_REVIEW",
                required=True,
                severity="MEDIUM",
                reason_code="RISK_REVIEW_REQUIRED",
                summary="Risk review is required before client progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=_DECISION_POLICY_VERSION,
            )
        )
    if gate == "CLIENT_CONSENT_REQUIRED":
        requirements.append(
            ProposalDecisionApprovalRequirement(
                approval_type="CLIENT_CONSENT",
                required=True,
                severity="MEDIUM",
                reason_code="CLIENT_CONSENT_REQUIRED",
                summary="Client consent is required before execution progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=_DECISION_POLICY_VERSION,
            )
        )
    if result.status == "BLOCKED" and missing_evidence:
        requirements.append(
            ProposalDecisionApprovalRequirement(
                approval_type="DATA_REMEDIATION",
                required=True,
                severity="HIGH",
                reason_code=missing_evidence[0].reason_code,
                summary="Blocking data or evidence remediation is required before progression.",
                blocking_until_approved=True,
                evidence_refs=missing_evidence[0].evidence_refs,
                policy_version=_DECISION_POLICY_VERSION,
            )
        )
    return requirements


def _build_evidence_refs(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> list[str]:
    refs = ["proposal.status"]
    if result.gate_decision is not None:
        refs.append("proposal.gate_decision")
    if result.suitability is not None:
        refs.append("proposal.suitability")
    if result.explanation.get("authority_resolution") is not None:
        refs.append("proposal.explanation.authority_resolution")
    for item in missing_evidence:
        refs.extend(item.evidence_refs)
    return sorted(set(refs))


def _build_action_items(
    *,
    decision_status: ProposalDecisionStatus,
    recommended_next_action: ProposalDecisionNextAction,
    primary_reason_code: str,
    primary_summary: str,
    evidence_refs: list[str],
) -> list[ProposalDecisionActionItem]:
    return [
        ProposalDecisionActionItem(
            action_code=recommended_next_action,
            reason_code=primary_reason_code,
            summary=primary_summary,
            evidence_refs=evidence_refs,
        )
    ]


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
