from __future__ import annotations

from src.core.advisory.decision_summary_models import (
    ProposalDecisionApprovalRequirement,
    ProposalDecisionMissingEvidence,
)
from src.core.proposal_result_models import ProposalResult
from src.core.suitability_models import SuitabilityIssue

SUITABILITY_APPROVAL_TYPES_BY_IMPLICATION = {
    "COMPLIANCE_REVIEW": "COMPLIANCE_REVIEW",
    "RISK_REVIEW": "RISK_REVIEW",
    "MANDATE_EXCEPTION_APPROVAL": "MANDATE_EXCEPTION_APPROVAL",
    "CLIENT_CONTEXT_REQUIRED": "DATA_REMEDIATION",
    "DATA_REMEDIATION": "DATA_REMEDIATION",
}


def build_approval_requirements(
    *,
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
    policy_version: str,
) -> list[ProposalDecisionApprovalRequirement]:
    requirements: dict[tuple[str, str], ProposalDecisionApprovalRequirement] = {}

    for requirement in _gate_approval_requirements(result, policy_version=policy_version):
        _merge_requirement(requirements, requirement)
    for requirement in _missing_evidence_approval_requirements(
        missing_evidence,
        policy_version=policy_version,
    ):
        _merge_requirement(requirements, requirement)
    for requirement in _suitability_approval_requirements(result, policy_version=policy_version):
        _merge_requirement(requirements, requirement)

    return sorted(
        requirements.values(),
        key=lambda item: (
            _severity_rank(item.severity),
            item.approval_type,
            item.reason_code,
        ),
    )


def _gate_approval_requirements(
    result: ProposalResult,
    *,
    policy_version: str,
) -> list[ProposalDecisionApprovalRequirement]:
    gate = result.gate_decision.gate if result.gate_decision is not None else None
    requirement_args = _gate_requirement_args(str(gate))
    if requirement_args is None:
        return []
    return [
        ProposalDecisionApprovalRequirement(
            **requirement_args,
            required=True,
            blocking_until_approved=False,
            evidence_refs=["proposal.gate_decision"],
            policy_version=policy_version,
        )
    ]


def _gate_requirement_args(gate: str) -> dict[str, str] | None:
    return {
        "COMPLIANCE_REVIEW_REQUIRED": {
            "approval_type": "COMPLIANCE_REVIEW",
            "severity": "HIGH",
            "reason_code": "COMPLIANCE_REVIEW_REQUIRED",
            "summary": "Compliance review is required before client progression.",
        },
        "RISK_REVIEW_REQUIRED": {
            "approval_type": "RISK_REVIEW",
            "severity": "MEDIUM",
            "reason_code": "RISK_REVIEW_REQUIRED",
            "summary": "Risk review is required before client progression.",
        },
        "CLIENT_CONSENT_REQUIRED": {
            "approval_type": "CLIENT_CONSENT",
            "severity": "MEDIUM",
            "reason_code": "CLIENT_CONSENT_REQUIRED",
            "summary": "Client consent is required before execution progression.",
        },
    }.get(gate)


def _missing_evidence_approval_requirements(
    missing_evidence: list[ProposalDecisionMissingEvidence],
    *,
    policy_version: str,
) -> list[ProposalDecisionApprovalRequirement]:
    return [
        requirement
        for item in missing_evidence
        if (requirement := _requirement_from_missing_evidence(item, policy_version=policy_version))
        is not None
    ]


def _requirement_from_missing_evidence(
    item: ProposalDecisionMissingEvidence,
    *,
    policy_version: str,
) -> ProposalDecisionApprovalRequirement | None:
    if not item.blocking:
        return None
    approval_type = _approval_type_for_missing_evidence(item.reason_code)
    if approval_type is None:
        return None
    return ProposalDecisionApprovalRequirement(
        approval_type=approval_type,
        required=True,
        severity="HIGH",
        reason_code=item.reason_code,
        summary=_missing_evidence_requirement_summary(item),
        blocking_until_approved=True,
        evidence_refs=item.evidence_refs,
        policy_version=policy_version,
    )


def _suitability_approval_requirements(
    result: ProposalResult,
    *,
    policy_version: str,
) -> list[ProposalDecisionApprovalRequirement]:
    if result.suitability is None:
        return []
    return [
        requirement
        for issue in result.suitability.issues
        if issue.status_change in {"NEW", "PERSISTENT"}
        if (
            requirement := _requirement_from_suitability_issue(
                issue=issue,
                policy_version=policy_version,
            )
        )
        is not None
    ]


def _requirement_from_suitability_issue(
    *,
    issue: SuitabilityIssue,
    policy_version: str,
) -> ProposalDecisionApprovalRequirement | None:
    approval_type = _approval_type_from_issue(issue)
    if approval_type is None:
        return None
    return ProposalDecisionApprovalRequirement(
        approval_type=approval_type,
        required=True,
        severity=issue.severity,
        reason_code=issue.issue_id,
        summary=issue.remediation or issue.summary,
        blocking_until_approved=approval_type in {"DATA_REMEDIATION", "MANDATE_EXCEPTION_APPROVAL"},
        evidence_refs=[f"proposal.suitability.issues.{issue.issue_key}"],
        policy_version=policy_version,
    )


def _approval_type_from_issue(issue: SuitabilityIssue) -> str | None:
    implication = issue.approval_implication
    if implication is None:
        return None
    return SUITABILITY_APPROVAL_TYPES_BY_IMPLICATION.get(implication)


def _approval_type_for_missing_evidence(reason_code: str) -> str | None:
    if reason_code in {
        "MISSING_REQUIRED_MARKET_PRICE",
        "MISSING_REQUIRED_FX_DATA",
        "MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
    }:
        return "DATA_REMEDIATION"
    if reason_code == "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE":
        return "MANDATE_EXCEPTION_APPROVAL"
    return None


def _missing_evidence_requirement_summary(item: ProposalDecisionMissingEvidence) -> str:
    if item.reason_code == "MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE":
        return "Mandate exception evidence is required before progressing the restricted product."
    return "Blocking data or evidence remediation is required before progression."


def _merge_requirement(
    requirements: dict[tuple[str, str], ProposalDecisionApprovalRequirement],
    requirement: ProposalDecisionApprovalRequirement,
) -> None:
    key = (requirement.approval_type, requirement.reason_code)
    existing = requirements.get(key)
    if existing is None:
        requirements[key] = requirement
        return
    merged_refs = sorted(set(existing.evidence_refs) | set(requirement.evidence_refs))
    requirements[key] = existing.model_copy(
        update={
            "severity": (
                requirement.severity
                if _severity_rank(requirement.severity) < _severity_rank(existing.severity)
                else existing.severity
            ),
            "blocking_until_approved": (
                existing.blocking_until_approved or requirement.blocking_until_approved
            ),
            "evidence_refs": merged_refs,
        }
    )


def _severity_rank(severity: str) -> int:
    return {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[severity]
