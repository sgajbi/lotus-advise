from typing import Dict, Iterable

from src.core.suitability_models import SuitabilityEvidence, SuitabilityIssue

from .suitability_policy import (
    HIGH,
    LOW,
    MEDIUM,
    SEVERITY_SORT,
    STATUS_SORT,
    IssueCandidate,
    _SuitabilityPolicyPack,
)


def build_suitability_issue(
    *,
    status_change: str,
    candidate: IssueCandidate,
    evidence: SuitabilityEvidence,
    policy_pack: _SuitabilityPolicyPack,
) -> SuitabilityIssue:
    return SuitabilityIssue(
        issue_id=candidate.issue_id,
        issue_key=candidate.issue_key,
        dimension=candidate.dimension,
        severity=candidate.severity,
        status_change=status_change,
        classification=(
            candidate.classification
            if candidate.classification == "UNKNOWN_DUE_TO_MISSING_EVIDENCE"
            else status_change
        ),
        summary=candidate.summary,
        remediation=candidate.remediation,
        approval_implication=candidate.approval_implication,
        details=candidate.details,
        evidence=evidence,
        policy_pack_id=policy_pack.pack_id,
        policy_version=policy_pack.version,
    )


def classify_issues(
    *,
    before_issues: Dict[str, IssueCandidate],
    after_issues: Dict[str, IssueCandidate],
    evidence: SuitabilityEvidence,
    policy_pack: _SuitabilityPolicyPack,
) -> list[SuitabilityIssue]:
    issue_keys = set(before_issues.keys()) | set(after_issues.keys())
    issues: list[SuitabilityIssue] = []

    for issue_key in issue_keys:
        in_before = issue_key in before_issues
        in_after = issue_key in after_issues

        if in_after and not in_before:
            issues.append(
                build_suitability_issue(
                    status_change="NEW",
                    candidate=after_issues[issue_key],
                    evidence=evidence,
                    policy_pack=policy_pack,
                )
            )
        elif in_before and in_after:
            issues.append(
                build_suitability_issue(
                    status_change="PERSISTENT",
                    candidate=after_issues[issue_key],
                    evidence=evidence,
                    policy_pack=policy_pack,
                )
            )
        elif in_before:
            issues.append(
                build_suitability_issue(
                    status_change="RESOLVED",
                    candidate=before_issues[issue_key],
                    evidence=evidence,
                    policy_pack=policy_pack,
                )
            )

    issues.sort(
        key=lambda issue: (
            STATUS_SORT[issue.status_change],
            SEVERITY_SORT[issue.severity],
            issue.dimension,
            issue.issue_key,
        )
    )

    return issues


def recommended_gate(issues: Iterable[SuitabilityIssue]) -> str:
    new_issues = [issue for issue in issues if issue.status_change == "NEW"]
    if any(issue.severity == HIGH for issue in new_issues):
        return "COMPLIANCE_REVIEW"
    if any(issue.severity == MEDIUM for issue in new_issues):
        return "RISK_REVIEW"
    return "NONE"


def highest_new_issue_severity(new_issues: list[SuitabilityIssue]) -> str | None:
    if any(issue.severity == HIGH for issue in new_issues):
        return HIGH
    if any(issue.severity == MEDIUM for issue in new_issues):
        return MEDIUM
    if any(issue.severity == LOW for issue in new_issues):
        return LOW
    return None
