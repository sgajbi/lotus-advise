from src.core.advisory.decision_summary_models import (
    ProposalDecisionConfidence,
    ProposalDecisionMissingEvidence,
    ProposalDecisionNextAction,
    ProposalDecisionStatus,
)
from src.core.proposal_result_models import ProposalResult


def derive_decision_status(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
) -> ProposalDecisionStatus:
    if result.status == "BLOCKED":
        return "BLOCKED_REMEDIATION_REQUIRED"

    blocking_missing_evidence = any(item.blocking for item in missing_evidence)
    if blocking_missing_evidence:
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


def primary_decision_reason_code(
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
    decision_status: ProposalDecisionStatus,
) -> str:
    if decision_status == "INSUFFICIENT_EVIDENCE" and missing_evidence:
        return str(missing_evidence[0].reason_code)
    gate_reason_code = _gate_reason_code(result)
    if gate_reason_code is not None:
        return gate_reason_code
    if missing_evidence:
        return str(missing_evidence[0].reason_code)
    return _reason_code_for_decision_status(decision_status)


def _gate_reason_code(result: ProposalResult) -> str | None:
    if result.gate_decision is None or not result.gate_decision.reasons:
        return None
    return str(result.gate_decision.reasons[0].reason_code)


def _reason_code_for_decision_status(decision_status: ProposalDecisionStatus) -> str:
    return {
        "READY_FOR_CLIENT_REVIEW": "PROPOSAL_READY_FOR_CLIENT_REVIEW",
        "REVISION_RECOMMENDED": "PROPOSAL_REVISION_RECOMMENDED",
        "REQUIRES_CLIENT_CONSENT": "CLIENT_CONSENT_REQUIRED",
        "REQUIRES_RISK_REVIEW": "RISK_REVIEW_REQUIRED",
        "REQUIRES_COMPLIANCE_REVIEW": "COMPLIANCE_REVIEW_REQUIRED",
        "INSUFFICIENT_EVIDENCE": "INSUFFICIENT_EVIDENCE",
    }.get(decision_status, "PROPOSAL_BLOCKED")


def primary_decision_summary(
    decision_status: ProposalDecisionStatus, primary_reason_code: str
) -> str:
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


def recommended_decision_next_action(
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
            if item.reason_code in {
                "MISSING_CLIENT_CONTEXT",
                "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
            }:
                return "REQUEST_CLIENT_CONTEXT"
            if item.reason_code in {
                "MISSING_MANDATE_CONTEXT",
                "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE",
            }:
                return "REQUEST_MANDATE_CONTEXT"
        return "REVISE_PROPOSAL"
    if decision_status == "REVISION_RECOMMENDED":
        return "REVISE_PROPOSAL"
    return "DISCUSS_WITH_CLIENT"


def decision_confidence(
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
