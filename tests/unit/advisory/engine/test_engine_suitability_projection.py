from src.core.common.suitability_policy import IssueCandidate, _SuitabilityPolicyPack
from src.core.common.suitability_projection import (
    classify_issues,
    highest_new_issue_severity,
    recommended_gate,
)
from src.core.suitability_models import SuitabilityEvidence, SuitabilityEvidenceSnapshotIds


def _candidate(
    issue_key: str,
    *,
    severity: str,
    dimension: str = "CONCENTRATION",
    classification: str = "NEW",
) -> IssueCandidate:
    return IssueCandidate(
        issue_key=issue_key,
        issue_id=f"ISSUE_{issue_key}",
        dimension=dimension,
        severity=severity,
        summary=f"{issue_key} summary",
        details={"issue_key": issue_key},
        classification=classification,
        remediation="Review the suitability issue before progressing.",
        approval_implication="RISK_REVIEW",
    )


def _evidence() -> SuitabilityEvidence:
    return SuitabilityEvidence(
        as_of="md_2026_02_19",
        snapshot_ids=SuitabilityEvidenceSnapshotIds(
            portfolio_snapshot_id="PB_SG_GLOBAL_BAL_001",
            market_data_snapshot_id="md_2026_02_19",
        ),
    )


def _policy_pack() -> _SuitabilityPolicyPack:
    return _SuitabilityPolicyPack(
        pack_id="global-private-banking-baseline",
        version="enterprise-suitability-policy.2026-04",
        state_evaluators=(),
        post_evaluators=(),
    )


def test_suitability_projection_classifies_and_orders_issue_transitions() -> None:
    before_issues = {
        "PERSISTENT_MEDIUM": _candidate("PERSISTENT_MEDIUM", severity="LOW"),
        "RESOLVED_LOW": _candidate("RESOLVED_LOW", severity="LOW"),
    }
    after_issues = {
        "NEW_HIGH": _candidate("NEW_HIGH", severity="HIGH"),
        "PERSISTENT_MEDIUM": _candidate("PERSISTENT_MEDIUM", severity="MEDIUM"),
    }

    issues = classify_issues(
        before_issues=before_issues,
        after_issues=after_issues,
        evidence=_evidence(),
        policy_pack=_policy_pack(),
    )

    assert [(issue.issue_key, issue.status_change, issue.severity) for issue in issues] == [
        ("NEW_HIGH", "NEW", "HIGH"),
        ("PERSISTENT_MEDIUM", "PERSISTENT", "MEDIUM"),
        ("RESOLVED_LOW", "RESOLVED", "LOW"),
    ]
    assert issues[1].details == {"issue_key": "PERSISTENT_MEDIUM"}
    assert issues[1].policy_pack_id == "global-private-banking-baseline"
    assert issues[1].policy_version == "enterprise-suitability-policy.2026-04"


def test_suitability_projection_preserves_unknown_missing_evidence_classification() -> None:
    issues = classify_issues(
        before_issues={},
        after_issues={
            "DQ_MISSING": _candidate(
                "DQ_MISSING",
                severity="LOW",
                dimension="DATA_QUALITY",
                classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
            )
        },
        evidence=_evidence(),
        policy_pack=_policy_pack(),
    )

    assert issues[0].status_change == "NEW"
    assert issues[0].classification == "UNKNOWN_DUE_TO_MISSING_EVIDENCE"


def test_suitability_projection_gate_uses_highest_new_issue_only() -> None:
    issues = classify_issues(
        before_issues={
            "PERSISTENT_HIGH": _candidate("PERSISTENT_HIGH", severity="HIGH"),
        },
        after_issues={
            "PERSISTENT_HIGH": _candidate("PERSISTENT_HIGH", severity="HIGH"),
            "NEW_MEDIUM": _candidate("NEW_MEDIUM", severity="MEDIUM"),
            "NEW_LOW": _candidate("NEW_LOW", severity="LOW"),
        },
        evidence=_evidence(),
        policy_pack=_policy_pack(),
    )

    assert (
        highest_new_issue_severity([issue for issue in issues if issue.status_change == "NEW"])
        == "MEDIUM"
    )
    assert recommended_gate(issues) == "RISK_REVIEW"
