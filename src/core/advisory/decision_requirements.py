from __future__ import annotations

from src.core.advisory.decision_summary_models import (
    ProposalDecisionApprovalRequirement,
    ProposalDecisionMissingEvidence,
)
from src.core.models import ProposalResult, SuitabilityIssue


def build_approval_requirements(
    *,
    result: ProposalResult,
    missing_evidence: list[ProposalDecisionMissingEvidence],
    policy_version: str,
) -> list[ProposalDecisionApprovalRequirement]:
    requirements: dict[tuple[str, str], ProposalDecisionApprovalRequirement] = {}

    gate = result.gate_decision.gate if result.gate_decision is not None else None
    if gate == "COMPLIANCE_REVIEW_REQUIRED":
        _merge_requirement(
            requirements,
            ProposalDecisionApprovalRequirement(
                approval_type="COMPLIANCE_REVIEW",
                required=True,
                severity="HIGH",
                reason_code="COMPLIANCE_REVIEW_REQUIRED",
                summary="Compliance review is required before client progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=policy_version,
            ),
        )
    if gate == "RISK_REVIEW_REQUIRED":
        _merge_requirement(
            requirements,
            ProposalDecisionApprovalRequirement(
                approval_type="RISK_REVIEW",
                required=True,
                severity="MEDIUM",
                reason_code="RISK_REVIEW_REQUIRED",
                summary="Risk review is required before client progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=policy_version,
            ),
        )
    if gate == "CLIENT_CONSENT_REQUIRED":
        _merge_requirement(
            requirements,
            ProposalDecisionApprovalRequirement(
                approval_type="CLIENT_CONSENT",
                required=True,
                severity="MEDIUM",
                reason_code="CLIENT_CONSENT_REQUIRED",
                summary="Client consent is required before execution progression.",
                blocking_until_approved=False,
                evidence_refs=["proposal.gate_decision"],
                policy_version=policy_version,
            ),
        )

    for item in missing_evidence:
        if not item.blocking:
            continue
        approval_type = _approval_type_for_missing_evidence(item.reason_code)
        if approval_type is None:
            continue
        _merge_requirement(
            requirements,
            ProposalDecisionApprovalRequirement(
                approval_type=approval_type,
                required=True,
                severity="HIGH",
                reason_code=item.reason_code,
                summary=_missing_evidence_requirement_summary(item),
                blocking_until_approved=True,
                evidence_refs=item.evidence_refs,
                policy_version=policy_version,
            ),
        )

    if result.suitability is not None:
        for issue in result.suitability.issues:
            if issue.status_change not in {"NEW", "PERSISTENT"}:
                continue
            requirement = _requirement_from_suitability_issue(
                issue=issue,
                policy_version=policy_version,
            )
            if requirement is None:
                continue
            _merge_requirement(requirements, requirement)

    return sorted(
        requirements.values(),
        key=lambda item: (
            _severity_rank(item.severity),
            item.approval_type,
            item.reason_code,
        ),
    )


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
    if implication == "COMPLIANCE_REVIEW":
        return "COMPLIANCE_REVIEW"
    if implication == "RISK_REVIEW":
        return "RISK_REVIEW"
    if implication == "MANDATE_EXCEPTION_APPROVAL":
        return "MANDATE_EXCEPTION_APPROVAL"
    if implication == "CLIENT_CONTEXT_REQUIRED":
        return "DATA_REMEDIATION"
    if implication == "DATA_REMEDIATION":
        return "DATA_REMEDIATION"
    return None


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
