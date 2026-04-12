from decimal import Decimal

from src.core.common.workflow_gates import evaluate_gate_decision
from src.core.models import (
    DiagnosticsData,
    EngineOptions,
    RuleResult,
    SuitabilityEvidence,
    SuitabilityEvidenceSnapshotIds,
    SuitabilityIssue,
    SuitabilityResult,
    SuitabilitySummary,
)


def _soft_rule(rule_id: str = "SOFT_POLICY_CHECK") -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        status="FAIL",
        severity="SOFT",
        measured=Decimal("1"),
        threshold={"limit": Decimal("0")},
        reason_code="SOFT_FAILURE",
        remediation_hint="review soft policy failure",
    )


def _hard_rule(rule_id: str = "HARD_POLICY_CHECK") -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        status="FAIL",
        severity="HARD",
        measured=Decimal("1"),
        threshold={"limit": Decimal("0")},
        reason_code="HARD_FAILURE",
        remediation_hint="fix hard policy failure",
    )


def _suitability_issue(*, severity: str, status_change: str = "NEW") -> SuitabilityIssue:
    return SuitabilityIssue(
        issue_id="SUIT_TEST",
        issue_key=f"ISSUE|{severity}|{status_change}",
        dimension="CONCENTRATION",
        severity=severity,
        status_change=status_change,
        summary="test suitability issue",
        details={},
        evidence=SuitabilityEvidence(
            as_of="md_1",
            snapshot_ids=SuitabilityEvidenceSnapshotIds(
                portfolio_snapshot_id="pf_1",
                market_data_snapshot_id="md_1",
            ),
        ),
    )


def _suitability_result(*issues: SuitabilityIssue) -> SuitabilityResult:
    new_issues = [issue for issue in issues if issue.status_change == "NEW"]
    highest = None
    if any(issue.severity == "HIGH" for issue in new_issues):
        highest = "HIGH"
    elif any(issue.severity == "MEDIUM" for issue in new_issues):
        highest = "MEDIUM"
    elif any(issue.severity == "LOW" for issue in new_issues):
        highest = "LOW"
    return SuitabilityResult(
        summary=SuitabilitySummary(
            new_count=len(new_issues),
            resolved_count=sum(1 for issue in issues if issue.status_change == "RESOLVED"),
            persistent_count=sum(1 for issue in issues if issue.status_change == "PERSISTENT"),
            highest_severity_new=highest,
        ),
        issues=list(issues),
        recommended_gate=(
            "COMPLIANCE_REVIEW"
            if highest == "HIGH"
            else "RISK_REVIEW"
            if highest == "MEDIUM"
            else "NONE"
        ),
    )


def _empty_diagnostics() -> DiagnosticsData:
    return DiagnosticsData(
        warnings=[],
        data_quality={"price_missing": [], "fx_missing": []},
    )


def test_workflow_gate_hard_failure_keeps_blocked_precedence() -> None:
    decision = evaluate_gate_decision(
        status="BLOCKED",
        rule_results=[_hard_rule(), _soft_rule()],
        suitability=_suitability_result(_suitability_issue(severity="HIGH")),
        diagnostics=_empty_diagnostics(),
        options=EngineOptions(enable_proposal_simulation=True),
        default_requires_client_consent=True,
    )

    assert decision.gate == "BLOCKED"
    assert decision.recommended_next_step == "FIX_INPUT"
    assert decision.summary.hard_fail_count == 1
    assert any(reason.reason_code.startswith("HARD_RULE_FAIL:") for reason in decision.reasons)


def test_workflow_gate_new_high_suitability_issue_drives_compliance_review() -> None:
    decision = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=_suitability_result(_suitability_issue(severity="HIGH")),
        diagnostics=_empty_diagnostics(),
        options=EngineOptions(enable_proposal_simulation=True),
        default_requires_client_consent=True,
    )

    assert decision.gate == "COMPLIANCE_REVIEW_REQUIRED"
    assert decision.recommended_next_step == "COMPLIANCE_REVIEW"
    assert decision.summary.new_high_suitability_count == 1


def test_workflow_gate_soft_review_precedes_client_consent_requirement() -> None:
    decision = evaluate_gate_decision(
        status="PENDING_REVIEW",
        rule_results=[_soft_rule()],
        suitability=None,
        diagnostics=_empty_diagnostics(),
        options=EngineOptions(
            enable_proposal_simulation=True,
            workflow_requires_client_consent=True,
        ),
        default_requires_client_consent=True,
    )

    assert decision.gate == "RISK_REVIEW_REQUIRED"
    assert decision.recommended_next_step == "RISK_REVIEW"
    assert decision.summary.soft_fail_count == 1


def test_workflow_gate_execution_ready_requires_clear_status_and_client_consent_state() -> None:
    decision = evaluate_gate_decision(
        status="READY",
        rule_results=[],
        suitability=None,
        diagnostics=_empty_diagnostics(),
        options=EngineOptions(
            enable_proposal_simulation=True,
            workflow_requires_client_consent=True,
            client_consent_already_obtained=True,
        ),
        default_requires_client_consent=True,
    )

    assert decision.gate == "EXECUTION_READY"
    assert decision.recommended_next_step == "EXECUTE"


def test_workflow_gate_data_quality_reasons_are_recorded_even_when_status_drives_blocking() -> None:
    decision = evaluate_gate_decision(
        status="BLOCKED",
        rule_results=[],
        suitability=None,
        diagnostics=DiagnosticsData(
            warnings=[],
            data_quality={"price_missing": ["EQ_1"], "fx_missing": ["USD/SGD"]},
        ),
        options=EngineOptions(enable_proposal_simulation=True),
        default_requires_client_consent=False,
    )

    reason_codes = {reason.reason_code for reason in decision.reasons}
    assert decision.gate == "BLOCKED"
    assert "DATA_QUALITY_MISSING_PRICE" in reason_codes
    assert "DATA_QUALITY_MISSING_FX" in reason_codes
