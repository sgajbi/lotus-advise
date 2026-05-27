from __future__ import annotations

import pytest

from src.core.advisor_cockpit import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    CockpitEvidenceRef,
    MeetingPreparationActionSource,
    MemoPackageBlockedActionSource,
    PolicyReviewActionSource,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
    build_approval_dependency_action,
    build_client_follow_up_action,
    build_first_wave_cockpit_actions,
    build_meeting_preparation_action,
    build_memo_package_blocked_action,
    build_policy_review_required_action,
    build_source_backed_action,
    build_supportability_degraded_action,
    build_unsupported_capability_action,
)

FIRST_WAVE_ACTION_FAMILIES = (
    "CLIENT_MEETING_PREPARATION",
    "PROPOSAL_READY_FOR_REVIEW",
    "PROPOSAL_BLOCKED_BY_SOURCE_GAP",
    "POLICY_REVIEW_REQUIRED",
    "APPROVAL_DEPENDENCY_AGING",
    "CLIENT_CONSENT_REQUIRED",
    "MEMO_PACKAGE_BLOCKED",
    "REPORT_RENDER_ARCHIVE_BLOCKED",
    "EXECUTION_HANDOFF_READY",
    "EXECUTION_STATUS_ATTENTION",
    "HOUSE_VIEW_IMPACT_REVIEW",
    "WORKSPACE_DRAFT_STALE",
    "CLIENT_FOLLOW_UP_REQUIRED",
    "SUPPORTABILITY_DEGRADED",
    "UNSUPPORTED_CAPABILITY",
)


def _evidence(evidence_id: str = "evidence_sg_001") -> CockpitEvidenceRef:
    return CockpitEvidenceRef(
        evidence_id=evidence_id,
        evidence_type="ADVISORY_SOURCE_EVIDENCE",
        source_system="lotus-advise",
        access_class="RESTRICTED_CUSTOMER_EVIDENCE",
        summary="Source-backed advisory evidence.",
    )


def test_policy_review_action_preserves_policy_boundary_and_client_ready_block() -> None:
    action = build_policy_review_required_action(
        PolicyReviewActionSource(
            policy_evaluation_id="policy_eval_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            proposal_id="proposal_sg_001",
            policy_result="PENDING_REVIEW",
            due_at="2026-05-28T08:00:00+00:00",
            source_timestamp="2026-05-27T07:30:00+00:00",
            lineage_id="lineage_policy_eval_sg_001",
            content_hash="sha256:policy-evaluation",
            correlation_id="corr-rfc26-canonical",
        )
    )

    assert action.action_item_id == "aci_policy_review_required_policy_eval_sg_001"
    assert action.action_family == "POLICY_REVIEW_REQUIRED"
    assert action.status == "PENDING_REVIEW"
    assert action.priority == "HIGH"
    assert action.owner_role == "COMPLIANCE_REVIEWER"
    assert action.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert action.proposal_id == "proposal_sg_001"
    assert action.policy_evaluation_id == "policy_eval_sg_001"
    assert action.reason_codes == ["POLICY_PENDING_REVIEW", "CLIENT_READY_BLOCKED"]
    assert action.evidence_refs[0].access_class == "RESTRICTED_CUSTOMER_EVIDENCE"
    assert action.source_readiness_gaps[0].gap_code == "POLICY_PENDING_REVIEW"
    assert action.lineage_refs[0].content_hash == "sha256:policy-evaluation"
    assert action.unsupported_capabilities == [
        "CLIENT_READY_PUBLICATION",
        "COMPLETED_POLICY_APPROVAL_AUTHORITY",
        "COMPLETED_POLICY_SIGN_OFF_AUTHORITY",
    ]
    assert action.correlation_id == "corr-rfc26-canonical"


def test_memo_package_blocked_action_keeps_memo_evidence_source_backed() -> None:
    action = build_memo_package_blocked_action(
        MemoPackageBlockedActionSource(
            memo_id="memo_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            blockage_code="MEMO_REVIEW_REQUIRED",
            lineage_id="lineage_memo_sg_001",
            content_hash="sha256:memo",
        )
    )

    assert action.action_family == "MEMO_PACKAGE_BLOCKED"
    assert action.status == "BLOCKED"
    assert action.owner_role == "REPORTING_OWNER"
    assert action.memo_id == "memo_sg_001"
    assert action.reason_codes == ["MEMO_REVIEW_REQUIRED", "CLIENT_READY_BLOCKED"]
    assert action.evidence_refs[0].evidence_type == "PROPOSAL_MEMO"
    assert action.source_readiness_gaps[0].source_family == "proposal_memo"
    assert action.unsupported_capabilities == ["CLIENT_READY_PUBLICATION"]


def test_meeting_preparation_action_defaults_portfolio_context_to_portfolio_ref() -> None:
    action = build_meeting_preparation_action(
        MeetingPreparationActionSource(
            preparation_id="prep_pb_sg_global_bal_001",
            context_ref="PB_SG_GLOBAL_BAL_001",
            context_type="PORTFOLIO",
            source_timestamp="2026-05-27T08:00:00+00:00",
        )
    )

    assert action.action_family == "CLIENT_MEETING_PREPARATION"
    assert action.status == "READY"
    assert action.priority == "MEDIUM"
    assert action.owner_role == "ADVISOR"
    assert action.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert action.reason_codes == ["MEETING_PREPARATION_READY"]
    assert action.evidence_refs[0].access_class == "CUSTOMER_CONSUMABLE_SUMMARY"


def test_client_follow_up_action_preserves_external_communication_boundary() -> None:
    action = build_client_follow_up_action(
        ClientFollowUpActionSource(
            follow_up_id="follow_up_proposal_sg_001_client_consent",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
            source_timestamp="2026-05-27T08:00:00+00:00",
        )
    )

    assert action.action_family == "CLIENT_FOLLOW_UP_REQUIRED"
    assert action.status == "READY"
    assert action.priority == "HIGH"
    assert action.owner_role == "ADVISOR"
    assert action.proposal_id == "proposal_sg_001"
    assert action.reason_codes == [
        "CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
        "EXTERNAL_CLIENT_COMMUNICATION_BLOCKED",
    ]
    assert action.evidence_refs[0].evidence_type == "CLIENT_FOLLOW_UP_REQUIREMENT"
    assert action.source_readiness_gaps[0].source_family == "proposal_lifecycle"
    assert action.unsupported_capabilities == [
        "EXTERNAL_CLIENT_COMMUNICATION",
        "CRM_SYSTEM_OF_RECORD",
    ]


def test_approval_dependency_action_preserves_supervisory_owner_boundary() -> None:
    action = build_approval_dependency_action(
        ApprovalDependencyActionSource(
            dependency_id="approval_dependency_proposal_sg_001_compliance",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            approval_type="COMPLIANCE",
            approval_status="PENDING",
            source_timestamp="2026-05-27T08:00:00+00:00",
        )
    )

    assert action.action_family == "APPROVAL_DEPENDENCY_AGING"
    assert action.status == "PENDING_REVIEW"
    assert action.priority == "HIGH"
    assert action.owner_role == "COMPLIANCE_REVIEWER"
    assert action.reason_codes == ["COMPLIANCE_APPROVAL_PENDING", "CLIENT_READY_BLOCKED"]
    assert action.evidence_refs[0].evidence_type == "PROPOSAL_APPROVAL_DEPENDENCY"
    assert action.source_readiness_gaps[0].owner_role == "COMPLIANCE_REVIEWER"
    assert action.unsupported_capabilities == [
        "CLIENT_READY_PUBLICATION",
        "COMPLETED_POLICY_APPROVAL_AUTHORITY",
    ]


def test_client_consent_dependency_preserves_external_communication_boundary() -> None:
    action = build_approval_dependency_action(
        ApprovalDependencyActionSource(
            dependency_id="approval_dependency_proposal_sg_001_client_consent",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            approval_type="CLIENT_CONSENT",
            approval_status="PENDING",
        )
    )

    assert action.action_family == "CLIENT_CONSENT_REQUIRED"
    assert action.owner_role == "ADVISOR"
    assert action.next_required_action == (
        "Record source-backed consent posture before execution readiness can change."
    )
    assert action.reason_codes == ["CLIENT_CONSENT_APPROVAL_PENDING", "CLIENT_READY_BLOCKED"]
    assert action.unsupported_capabilities == [
        "EXTERNAL_CLIENT_COMMUNICATION",
        "CRM_SYSTEM_OF_RECORD",
    ]


def test_supportability_action_is_blocking_when_dependency_is_unavailable() -> None:
    action = build_supportability_degraded_action(
        SupportabilityDegradedActionSource(
            dependency="lotus-report",
            state="UNAVAILABLE",
            reason_code="REPORT_PACKAGE_UNAVAILABLE",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
        )
    )

    assert action.action_family == "SUPPORTABILITY_DEGRADED"
    assert action.status == "BLOCKED"
    assert action.priority == "HIGH"
    assert action.dependency_readiness[0].dependency == "lotus-report"
    assert action.dependency_readiness[0].state == "UNAVAILABLE"
    assert action.reason_codes == ["REPORT_PACKAGE_UNAVAILABLE", "DEPENDENCY_UNAVAILABLE"]


def test_unsupported_capability_action_is_visible_not_silent() -> None:
    action = build_unsupported_capability_action(
        UnsupportedCapabilityActionSource(
            capability="CLIENT_READY_PUBLICATION",
            context_ref="PB_SG_GLOBAL_BAL_001",
            reason_code="CLIENT_READY_PUBLICATION_NOT_SUPPORTED",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
        )
    )

    assert action.action_family == "UNSUPPORTED_CAPABILITY"
    assert action.status == "BLOCKED"
    assert action.priority == "INFORMATIONAL"
    assert action.owner_role == "SYSTEM"
    assert action.unsupported_capabilities == ["CLIENT_READY_PUBLICATION"]
    assert action.next_required_action == "Do not present this capability as supported."


def test_source_backed_action_builder_constructs_each_cockpit_family_with_evidence() -> None:
    actions = [
        build_source_backed_action(
            CockpitActionConstructionInput(
                source_action_id=f"source_{family}",
                action_family=family,
                status="READY",
                priority="LOW",
                owner_role="ADVISOR",
                title="Review advisory action",
                next_required_action="Review the source-backed advisory evidence.",
                reason_codes=[f"{family}_READY"],
                source_refs=CockpitActionSourceRefs(portfolio_id="PB_SG_GLOBAL_BAL_001"),
                evidence_refs=[_evidence(f"evidence_{family}")],
            )
        )
        for family in FIRST_WAVE_ACTION_FAMILIES
    ]

    assert [action.action_family for action in actions] == list(FIRST_WAVE_ACTION_FAMILIES)
    assert all(action.owning_system == "lotus-advise" for action in actions)
    assert all(action.portfolio_id == "PB_SG_GLOBAL_BAL_001" for action in actions)
    assert all(action.evidence_refs for action in actions)


def test_source_backed_action_builder_rejects_unexplained_actions() -> None:
    with pytest.raises(ValueError, match="at least one reason code"):
        build_source_backed_action(
            CockpitActionConstructionInput(
                source_action_id="source_missing_reason",
                action_family="CLIENT_FOLLOW_UP_REQUIRED",
                status="READY",
                priority="LOW",
                owner_role="ADVISOR",
                title="Review advisory action",
                next_required_action="Review the source-backed advisory evidence.",
                reason_codes=[],
                evidence_refs=[_evidence()],
            )
        )

    with pytest.raises(ValueError, match="requires evidence"):
        build_source_backed_action(
            CockpitActionConstructionInput(
                source_action_id="source_missing_evidence",
                action_family="CLIENT_FOLLOW_UP_REQUIRED",
                status="READY",
                priority="LOW",
                owner_role="ADVISOR",
                title="Review advisory action",
                next_required_action="Review the source-backed advisory evidence.",
                reason_codes=["FOLLOW_UP_READY"],
            )
        )


def test_first_wave_builder_returns_stable_priority_order() -> None:
    actions = build_first_wave_cockpit_actions(
        policy_reviews=[
            PolicyReviewActionSource(
                policy_evaluation_id="policy_eval_sg_001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                policy_result="PENDING_REVIEW",
                materiality_rank=80,
            )
        ],
        memo_blocks=[
            MemoPackageBlockedActionSource(
                memo_id="memo_sg_001",
                proposal_id="proposal_sg_001",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                blockage_code="MEMO_REVIEW_REQUIRED",
                materiality_rank=60,
            )
        ],
        meeting_preparations=[
            MeetingPreparationActionSource(
                preparation_id="prep_sg_001",
                context_ref="PB_SG_GLOBAL_BAL_001",
            )
        ],
        client_follow_ups=[
            ClientFollowUpActionSource(
                follow_up_id="follow_up_sg_001",
                proposal_id="proposal_sg_001",
                follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
            )
        ],
    )

    assert [action.action_family for action in actions] == [
        "POLICY_REVIEW_REQUIRED",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_FOLLOW_UP_REQUIRED",
        "CLIENT_MEETING_PREPARATION",
    ]
