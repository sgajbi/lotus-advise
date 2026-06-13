from collections.abc import Iterable
from typing import Dict

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

_GATE_BY_NEW_SEVERITY = {
    HIGH: "COMPLIANCE_REVIEW",
    MEDIUM: "RISK_REVIEW",
    LOW: "NONE",
}
_SEVERITY_DESCENDING = (HIGH, MEDIUM, LOW)


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
        classified_issue = _classified_issue(
            issue_key=issue_key,
            before_issues=before_issues,
            after_issues=after_issues,
            evidence=evidence,
            policy_pack=policy_pack,
        )
        if classified_issue is not None:
            issues.append(classified_issue)

    return sorted(issues, key=_issue_sort_key)


def _classified_issue(
    *,
    issue_key: str,
    before_issues: Dict[str, IssueCandidate],
    after_issues: Dict[str, IssueCandidate],
    evidence: SuitabilityEvidence,
    policy_pack: _SuitabilityPolicyPack,
) -> SuitabilityIssue | None:
    status_change = _issue_status_change(
        in_before=issue_key in before_issues,
        in_after=issue_key in after_issues,
    )
    if status_change is None:
        return None
    return build_suitability_issue(
        status_change=status_change,
        candidate=_issue_candidate(
            issue_key=issue_key,
            status_change=status_change,
            before_issues=before_issues,
            after_issues=after_issues,
        ),
        evidence=evidence,
        policy_pack=policy_pack,
    )


def _issue_status_change(*, in_before: bool, in_after: bool) -> str | None:
    if in_after:
        return "PERSISTENT" if in_before else "NEW"
    if in_before:
        return "RESOLVED"
    return None


def _issue_candidate(
    *,
    issue_key: str,
    status_change: str,
    before_issues: Dict[str, IssueCandidate],
    after_issues: Dict[str, IssueCandidate],
) -> IssueCandidate:
    if status_change == "RESOLVED":
        return before_issues[issue_key]
    return after_issues[issue_key]


def _issue_sort_key(issue: SuitabilityIssue) -> tuple[int, int, str, str]:
    return (
        STATUS_SORT[issue.status_change],
        SEVERITY_SORT[issue.severity],
        issue.dimension,
        issue.issue_key,
    )


def recommended_gate(issues: Iterable[SuitabilityIssue]) -> str:
    highest_severity = highest_new_issue_severity(
        [issue for issue in issues if issue.status_change == "NEW"]
    )
    if highest_severity is None:
        return "NONE"
    return _GATE_BY_NEW_SEVERITY[highest_severity]


def highest_new_issue_severity(new_issues: list[SuitabilityIssue]) -> str | None:
    severities = {issue.severity for issue in new_issues}
    return next(
        (severity for severity in _SEVERITY_DESCENDING if severity in severities),
        None,
    )
