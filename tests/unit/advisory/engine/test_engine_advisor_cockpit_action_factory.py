from __future__ import annotations

import pytest

from src.core.advisor_cockpit import (
    ApprovalDependencyActionSource,
    ClientFollowUpActionSource,
    CockpitActionConstructionInput,
    CockpitActionSourceRefs,
    CockpitEvidenceRef,
    CockpitLineageRef,
    ExecutionHandoffReadyActionSource,
    ExecutionStatusAttentionActionSource,
    HouseViewImpactActionSource,
    MeetingPreparationActionSource,
    MemoPackageBlockedActionSource,
    PolicyReviewActionSource,
    ReportRenderArchiveActionSource,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
    build_approval_dependency_action,
    build_client_follow_up_action,
    build_execution_handoff_ready_action,
    build_execution_status_attention_action,
    build_house_view_impact_action,
    build_meeting_preparation_action,
    build_memo_package_blocked_action,
    build_policy_review_required_action,
    build_report_render_archive_action,
    build_source_backed_action,
    build_source_backed_cockpit_actions,
    build_supportability_degraded_action,
    build_unsupported_capability_action,
)

CANONICAL_COCKPIT_ACTION_FAMILIES = (
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


def test_policy_review_action_bounds_oversized_source_projection_references() -> None:
    oversized_policy_evaluation_id = f"policy_eval_{'sg_' * 80}"
    oversized_summary = "Source-backed policy evidence requires review. " * 40

    action = build_policy_review_required_action(
        PolicyReviewActionSource(
            policy_evaluation_id=oversized_policy_evaluation_id,
            portfolio_id=f"PB_SG_GLOBAL_BAL_{'001_' * 40}",
            proposal_id=f"proposal_{'sg_' * 80}",
            policy_result="PENDING_REVIEW",
            summary=oversized_summary,
            lineage_id=f"lineage_policy_eval_{'sg_' * 80}",
            content_hash=f"sha256:{'policy-evaluation' * 20}",
            correlation_id=f"corr_{'projection_' * 40}",
        )
    )

    assert len(action.action_item_id) <= 160
    assert len(action.policy_evaluation_id or "") <= 160
    assert len(action.proposal_id or "") <= 160
    assert len(action.portfolio_id or "") <= 160
    assert len(action.evidence_refs[0].evidence_id) <= 160
    assert len(action.evidence_refs[0].summary) <= 512
    assert len(action.lineage_refs[0].lineage_id) <= 160
    assert len(action.lineage_refs[0].content_hash or "") <= 160
    assert (action.lineage_refs[0].content_hash or "").startswith("sha256:")
    assert len(action.correlation_id or "") <= 160
    assert action.evidence_refs[0].summary.endswith("...")


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


def test_source_actions_use_initial_sla_band_when_due_at_is_present() -> None:
    due_action = build_client_follow_up_action(
        ClientFollowUpActionSource(
            follow_up_id="follow_up_due_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
            due_at="2026-05-28T08:00:00+00:00",
        )
    )
    undated_action = build_client_follow_up_action(
        ClientFollowUpActionSource(
            follow_up_id="follow_up_not_due_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
        )
    )

    assert due_action.sla_age_band == "DUE_SOON"
    assert undated_action.sla_age_band == "NOT_APPLICABLE"


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


def test_rejected_approval_dependency_is_blocking_and_critical() -> None:
    action = build_approval_dependency_action(
        ApprovalDependencyActionSource(
            dependency_id="approval_dependency_proposal_sg_001_risk",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            approval_type="RISK",
            approval_status="REJECTED",
            summary="Risk approval rejected because suitability evidence is incomplete.",
        )
    )

    assert action.action_family == "APPROVAL_DEPENDENCY_AGING"
    assert action.status == "BLOCKED"
    assert action.priority == "CRITICAL"
    assert action.owner_role == "INVESTMENT_DESK"
    assert action.reason_codes == ["RISK_APPROVAL_REJECTED", "CLIENT_READY_BLOCKED"]
    assert action.source_readiness_gaps[0].gap_code == "RISK_APPROVAL_REJECTED"
    assert action.source_readiness_gaps[0].owner_role == "INVESTMENT_DESK"
    assert action.unsupported_capabilities == [
        "CLIENT_READY_PUBLICATION",
        "COMPLETED_POLICY_APPROVAL_AUTHORITY",
    ]


def test_report_render_archive_action_preserves_downstream_owner_boundary() -> None:
    action = build_report_render_archive_action(
        ReportRenderArchiveActionSource(
            readiness_id="report_archive_readiness_memo_sg_001",
            memo_id="memo_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            readiness_code="REPORT_PACKAGE_NOT_REQUESTED",
            content_hash="sha256:memo",
            lineage_id="proposal_memo:memo_sg_001",
        )
    )

    assert action.action_family == "REPORT_RENDER_ARCHIVE_BLOCKED"
    assert action.status == "BLOCKED"
    assert action.owner_role == "REPORTING_OWNER"
    assert action.memo_id == "memo_sg_001"
    assert action.report_ref == "report_archive_readiness_memo_sg_001"
    assert action.reason_codes == ["REPORT_PACKAGE_NOT_REQUESTED", "CLIENT_READY_BLOCKED"]
    assert action.source_readiness_gaps[0].source_family == "report_render_archive"
    assert action.unsupported_capabilities == ["CLIENT_READY_PUBLICATION"]


def test_execution_handoff_and_status_actions_preserve_oms_boundary() -> None:
    handoff = build_execution_handoff_ready_action(
        ExecutionHandoffReadyActionSource(
            handoff_id="execution_handoff_ready_proposal_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
        )
    )
    status = build_execution_status_attention_action(
        ExecutionStatusAttentionActionSource(
            execution_ref="execution_request_sg_001",
            proposal_id="proposal_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            handoff_status="REJECTED",
        )
    )

    assert handoff.action_family == "EXECUTION_HANDOFF_READY"
    assert handoff.status == "READY"
    assert handoff.owner_role == "EXECUTION_OWNER"
    assert handoff.unsupported_capabilities == ["OMS_ORDER_LIFECYCLE"]
    assert status.action_family == "EXECUTION_STATUS_ATTENTION"
    assert status.status == "BLOCKED"
    assert status.priority == "HIGH"
    assert status.reason_codes == ["EXECUTION_STATUS_REJECTED", "OMS_ORDER_LIFECYCLE_BLOCKED"]
    assert status.unsupported_capabilities == ["OMS_ORDER_LIFECYCLE"]


def test_house_view_impact_action_requires_source_backed_cohort() -> None:
    action = build_house_view_impact_action(
        HouseViewImpactActionSource(
            cohort_id="thv_cohort_sg_001",
            tactical_view_id="thv_2026_05_asia_duration",
            tactical_view_version="2026.05",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            impact_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
            content_hash="sha256:house-view-cohort",
        )
    )

    assert action.action_family == "HOUSE_VIEW_IMPACT_REVIEW"
    assert action.status == "PENDING_REVIEW"
    assert action.owner_role == "PORTFOLIO_MANAGER"
    assert action.next_required_action == (
        "Review the source-backed tactical house-view cohort before discretionary "
        "portfolio-management actioning."
    )
    assert action.evidence_refs[0].evidence_type == "TACTICAL_HOUSE_VIEW_COHORT"
    assert action.lineage_refs[0].lineage_id == "tactical_house_view_cohort:thv_cohort_sg_001"
    assert action.lineage_refs[0].content_hash == "sha256:house-view-cohort"


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
        for family in CANONICAL_COCKPIT_ACTION_FAMILIES
    ]

    assert [action.action_family for action in actions] == list(CANONICAL_COCKPIT_ACTION_FAMILIES)
    assert all(action.owning_system == "lotus-advise" for action in actions)
    assert all(action.portfolio_id == "PB_SG_GLOBAL_BAL_001" for action in actions)
    assert all(action.evidence_refs for action in actions)
    assert all(action.lineage_refs for action in actions)
    assert actions[0].lineage_refs[0].lineage_id == (
        f"{actions[0].action_family.lower()}:source_{actions[0].action_family}"
    )


def test_source_backed_action_builder_preserves_explicit_lineage_refs() -> None:
    action = build_source_backed_action(
        CockpitActionConstructionInput(
            source_action_id="source_explicit_lineage",
            action_family="CLIENT_FOLLOW_UP_REQUIRED",
            status="READY",
            priority="LOW",
            owner_role="ADVISOR",
            title="Review advisory action",
            next_required_action="Review the source-backed advisory evidence.",
            reason_codes=["FOLLOW_UP_READY"],
            evidence_refs=[_evidence()],
            lineage_refs=[
                CockpitLineageRef(
                    lineage_id="proposal_lifecycle:proposal_sg_001",
                    source_system="lotus-advise",
                    content_hash="sha256:proposal-lifecycle",
                )
            ],
        )
    )

    assert [lineage.lineage_id for lineage in action.lineage_refs] == [
        "proposal_lifecycle:proposal_sg_001"
    ]
    assert [lineage.content_hash for lineage in action.lineage_refs] == [
        "sha256:proposal-lifecycle"
    ]


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


def test_source_backed_builder_returns_stable_priority_order() -> None:
    actions = build_source_backed_cockpit_actions(
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


def test_source_backed_builder_aggregates_every_source_family() -> None:
    actions = build_source_backed_cockpit_actions(
        policy_reviews=[
            PolicyReviewActionSource(
                policy_evaluation_id="policy_eval_sg_all",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                policy_result="PENDING_REVIEW",
            )
        ],
        memo_blocks=[
            MemoPackageBlockedActionSource(
                memo_id="memo_sg_all",
                proposal_id="proposal_sg_all",
                blockage_code="MEMO_REVIEW_REQUIRED",
            )
        ],
        meeting_preparations=[
            MeetingPreparationActionSource(
                preparation_id="prep_sg_all",
                context_ref="PB_SG_GLOBAL_BAL_001",
            )
        ],
        client_follow_ups=[
            ClientFollowUpActionSource(
                follow_up_id="follow_up_sg_all",
                proposal_id="proposal_sg_all",
                follow_up_code="CLIENT_CONSENT_FOLLOW_UP_REQUIRED",
            )
        ],
        approval_dependencies=[
            ApprovalDependencyActionSource(
                dependency_id="approval_dependency_sg_all",
                proposal_id="proposal_sg_all",
                approval_type="COMPLIANCE",
                approval_status="PENDING",
            )
        ],
        report_render_archive_items=[
            ReportRenderArchiveActionSource(
                readiness_id="report_archive_readiness_sg_all",
                memo_id="memo_sg_all",
                proposal_id="proposal_sg_all",
                readiness_code="REPORT_PACKAGE_NOT_REQUESTED",
            )
        ],
        execution_handoffs=[
            ExecutionHandoffReadyActionSource(
                handoff_id="execution_handoff_sg_all",
                proposal_id="proposal_sg_all",
            )
        ],
        execution_status_items=[
            ExecutionStatusAttentionActionSource(
                execution_ref="execution_status_sg_all",
                proposal_id="proposal_sg_all",
                handoff_status="REJECTED",
            )
        ],
        house_view_impacts=[
            HouseViewImpactActionSource(
                cohort_id="house_view_sg_all",
                tactical_view_id="tactical_view_sg_all",
                tactical_view_version="2026.06",
                portfolio_id="PB_SG_GLOBAL_BAL_001",
                impact_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
            )
        ],
        supportability_events=[
            SupportabilityDegradedActionSource(
                dependency="lotus-report",
                state="DEGRADED",
                reason_code="REPORT_PACKAGE_DEGRADED",
            )
        ],
        unsupported_capabilities=[
            UnsupportedCapabilityActionSource(
                capability="CLIENT_READY_PUBLICATION",
                context_ref="PB_SG_GLOBAL_BAL_001",
                reason_code="CLIENT_READY_PUBLICATION_NOT_SUPPORTED",
            )
        ],
    )

    assert {action.action_family for action in actions} == {
        "POLICY_REVIEW_REQUIRED",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_MEETING_PREPARATION",
        "CLIENT_FOLLOW_UP_REQUIRED",
        "APPROVAL_DEPENDENCY_AGING",
        "REPORT_RENDER_ARCHIVE_BLOCKED",
        "EXECUTION_HANDOFF_READY",
        "EXECUTION_STATUS_ATTENTION",
        "HOUSE_VIEW_IMPACT_REVIEW",
        "SUPPORTABILITY_DEGRADED",
        "UNSUPPORTED_CAPABILITY",
    }
    assert len(actions) == 11
