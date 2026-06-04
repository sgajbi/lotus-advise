from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.advisor_cockpit import (
    ACTIVE_PROPOSAL_STATES,
    APPROVAL_DEPENDENCY_STATES,
    COCKPIT_POLICY_REVIEW_STATUSES,
    COCKPIT_SOURCE_BATCH_MAX_ITEMS,
    FOLLOW_UP_PROPOSAL_STATES,
    AdvisorCockpitSourceBatch,
    AdvisorCockpitSourceReadModel,
    HouseViewImpactActionSource,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
    build_advisor_cockpit_source_read_model,
)
from src.core.policy_packs.persistence_models import PolicyEvaluationRecord
from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalWorkflowEventRecord,
)

AS_OF = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[4]


def test_source_read_model_exports_cockpit_source_filters() -> None:
    assert "COMPLIANCE_REVIEW" in ACTIVE_PROPOSAL_STATES
    assert "EXECUTED" not in ACTIVE_PROPOSAL_STATES
    assert FOLLOW_UP_PROPOSAL_STATES == frozenset({"AWAITING_CLIENT_CONSENT"})
    assert APPROVAL_DEPENDENCY_STATES == {
        "RISK_REVIEW": "RISK",
        "COMPLIANCE_REVIEW": "COMPLIANCE",
        "AWAITING_CLIENT_CONSENT": "CLIENT_CONSENT",
    }
    assert COCKPIT_POLICY_REVIEW_STATUSES == frozenset({"PENDING_REVIEW", "BLOCKED"})
    assert COCKPIT_SOURCE_BATCH_MAX_ITEMS == 100


def test_source_read_model_delegates_source_projection_helpers() -> None:
    read_model_source = (REPO_ROOT / "src/core/advisor_cockpit/source_read_model.py").read_text(
        encoding="utf-8"
    )
    projection_source = (REPO_ROOT / "src/core/advisor_cockpit/source_projection.py").read_text(
        encoding="utf-8"
    )
    policy_memo_source = (
        REPO_ROOT / "src/core/advisor_cockpit/source_projection_policy_memo.py"
    ).read_text(encoding="utf-8")

    for helper_name in (
        "_approval_dependency_source",
        "_report_readiness_source",
        "_execution_status_source",
    ):
        assert f"def {helper_name}(" not in read_model_source
        assert f"def {helper_name}(" in projection_source

    for helper_name in (
        "_policy_review_source",
        "_memo_block_source",
        "_memo_blockage_code",
    ):
        assert f"def {helper_name}(" not in read_model_source
        assert f"def {helper_name}(" not in projection_source
        assert f"def {helper_name}(" in policy_memo_source


def test_source_projection_delegates_policy_and_memo_projection_rules() -> None:
    projection_source = (REPO_ROOT / "src/core/advisor_cockpit/source_projection.py").read_text(
        encoding="utf-8"
    )
    policy_memo_source = (
        REPO_ROOT / "src/core/advisor_cockpit/source_projection_policy_memo.py"
    ).read_text(encoding="utf-8")

    assert "from src.core.advisor_cockpit.source_projection_policy_memo import" in (
        projection_source
    )
    assert "COCKPIT_POLICY_REVIEW_STATUSES" in projection_source
    assert "build_policy_review_sources" in projection_source
    assert "build_memo_block_sources" in projection_source
    assert "COCKPIT_POLICY_REVIEW_STATUSES = frozenset" not in projection_source
    assert "COCKPIT_POLICY_REVIEW_STATUSES = frozenset" in policy_memo_source


def test_source_read_model_rejects_unbounded_source_batches() -> None:
    with pytest.raises(ValidationError, match="List should have at most 100 items"):
        AdvisorCockpitSourceBatch(
            proposals=[
                _proposal("COMPLIANCE_REVIEW", proposal_id=f"proposal_sg_{index:03d}")
                for index in range(COCKPIT_SOURCE_BATCH_MAX_ITEMS + 1)
            ]
        )


def _proposal(state: str, proposal_id: str = "proposal_sg_001") -> ProposalRecord:
    return ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        created_by="advisor_sg_001",
        created_at=AS_OF,
        last_event_at=AS_OF,
        current_state=state,
        current_version_no=1,
        title="Singapore global balanced proposal",
    )


def _policy_evaluation(
    status: str,
    evaluation_id: str = "policy_eval_sg_001",
) -> PolicyEvaluationRecord:
    return PolicyEvaluationRecord(
        evaluation_id=evaluation_id,
        proposal_id="proposal_sg_001",
        proposal_version_id="ppv_sg_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        generated_at="2026-05-27T08:00:00+00:00",
        created_by="advisor_sg_001",
        evaluation_status=status,
        policy_content_hash="sha256:policy-content",
        source_evidence_hash="sha256:source-evidence",
        evaluation_hash=f"sha256:{evaluation_id}",
        evaluation_json={"evaluation_status": status},
    )


def _memo(
    *,
    memo_status: str = "BLOCKED",
    lifecycle_status: str = "FINALIZED",
    review_events: list[dict] | None = None,
    memo_id: str = "memo_sg_001",
    report_events: list[dict] | None = None,
    archive_refs: list[dict] | None = None,
) -> ProposalMemoRecord:
    return ProposalMemoRecord(
        memo_id=memo_id,
        proposal_id="proposal_sg_001",
        proposal_version_no=1,
        memo_version="advisory-proposal-memo-evidence-pack.v1",
        memo_status=memo_status,
        lifecycle_status=lifecycle_status,
        created_by="advisor_sg_001",
        created_at=AS_OF,
        source_input_hash="sha256:source-input",
        memo_hash=f"sha256:{memo_id}",
        memo_json={"memo_id": memo_id, "status": memo_status},
        review_events_json=review_events or [],
        report_package_events_json=report_events or [],
        archive_refs_json=archive_refs or [],
    )


def _approval(
    *,
    proposal_id: str,
    approval_type: str,
    approved: bool,
    approval_id: str = "approval_sg_001",
) -> ProposalApprovalRecordData:
    return ProposalApprovalRecordData(
        approval_id=approval_id,
        proposal_id=proposal_id,
        approval_type=approval_type,
        approved=approved,
        actor_id="reviewer_sg_001",
        occurred_at=AS_OF,
        details_json={"source": "unit-test"},
        related_version_no=1,
    )


def _event(
    *,
    proposal_id: str,
    event_type: str,
    event_id: str,
    reason: dict | None = None,
) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal_id,
        event_type=event_type,
        from_state="EXECUTION_READY",
        to_state="EXECUTION_READY",
        actor_id="execution_owner_sg_001",
        occurred_at=AS_OF,
        reason_json=reason or {},
        related_version_no=1,
    )


def test_source_read_model_maps_preloaded_sources_to_sorted_cockpit_actions() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[
                _proposal("COMPLIANCE_REVIEW", proposal_id="proposal_sg_001"),
                _proposal("AWAITING_CLIENT_CONSENT", proposal_id="proposal_sg_consent"),
                _proposal("EXECUTION_READY", proposal_id="proposal_sg_execution_ready"),
                _proposal("EXECUTED", proposal_id="proposal_sg_executed"),
            ],
            policy_evaluations=[
                _policy_evaluation("PENDING_REVIEW", "policy_eval_sg_pending"),
                _policy_evaluation("READY", "policy_eval_sg_ready"),
            ],
            memos=[
                _memo(memo_status="BLOCKED", memo_id="memo_sg_blocked"),
                _memo(
                    memo_status="READY",
                    memo_id="memo_sg_ready",
                    review_events=[{"event_type": "MEMO_REVIEW_RECORDED"}],
                ),
            ],
            approvals=[
                _approval(
                    proposal_id="proposal_sg_executed",
                    approval_type="CLIENT_CONSENT",
                    approved=True,
                )
            ],
            workflow_events=[
                _event(
                    proposal_id="proposal_sg_execution_ready",
                    event_type="EXECUTION_REQUESTED",
                    event_id="pwe_001_execution_requested",
                    reason={"execution_request_id": "execution_request_sg_001"},
                ),
                _event(
                    proposal_id="proposal_sg_execution_ready",
                    event_type="EXECUTION_REJECTED",
                    event_id="pwe_002_execution_rejected",
                    reason={"execution_request_id": "execution_request_sg_001"},
                ),
            ],
            house_view_impacts=[
                HouseViewImpactActionSource(
                    cohort_id="thv_cohort_sg_001",
                    tactical_view_id="thv_2026_05_asia_duration",
                    tactical_view_version="2026.05",
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                    impact_code="TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED",
                )
            ],
            supportability_events=[
                SupportabilityDegradedActionSource(
                    dependency="lotus-report",
                    state="UNAVAILABLE",
                    reason_code="REPORT_PACKAGE_UNAVAILABLE",
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                )
            ],
            unsupported_capabilities=[
                UnsupportedCapabilityActionSource(
                    capability="CLIENT_READY_PUBLICATION",
                    context_ref="PB_SG_GLOBAL_BAL_001",
                    reason_code="CLIENT_READY_PUBLICATION_NOT_SUPPORTED",
                    portfolio_id="PB_SG_GLOBAL_BAL_001",
                )
            ],
        )
    )

    assert isinstance(read_model, AdvisorCockpitSourceReadModel)
    assert read_model.source_counts == {
        "proposals": 4,
        "policy_evaluations": 2,
        "memos": 2,
        "approvals": 1,
        "workflow_events": 2,
        "house_view_impacts": 1,
        "supportability_events": 1,
        "unsupported_capabilities": 1,
    }
    assert [source.policy_evaluation_id for source in read_model.policy_reviews] == [
        "policy_eval_sg_pending"
    ]
    assert [source.memo_id for source in read_model.memo_blocks] == ["memo_sg_blocked"]
    assert [source.portfolio_id for source in read_model.memo_blocks] == ["PB_SG_GLOBAL_BAL_001"]
    assert [source.proposal_id for source in read_model.meeting_preparations] == [
        "proposal_sg_001",
        "proposal_sg_consent",
        "proposal_sg_execution_ready",
    ]
    assert [source.proposal_id for source in read_model.client_follow_ups] == [
        "proposal_sg_consent"
    ]
    assert [source.approval_type for source in read_model.approval_dependencies] == [
        "COMPLIANCE",
        "CLIENT_CONSENT",
    ]
    assert [source.readiness_code for source in read_model.report_render_archive_items] == [
        "REPORT_PACKAGE_NOT_REQUESTED"
    ]
    assert [source.portfolio_id for source in read_model.report_render_archive_items] == [
        "PB_SG_GLOBAL_BAL_001"
    ]
    assert read_model.execution_handoffs == []
    assert [source.handoff_status for source in read_model.execution_status_items] == ["REJECTED"]
    assert [source.impact_code for source in read_model.house_view_impacts] == [
        "TACTICAL_HOUSE_VIEW_PORTFOLIO_AFFECTED"
    ]
    assert [action.action_family for action in read_model.action_items] == [
        "POLICY_REVIEW_REQUIRED",
        "APPROVAL_DEPENDENCY_AGING",
        "EXECUTION_STATUS_ATTENTION",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_CONSENT_REQUIRED",
        "CLIENT_FOLLOW_UP_REQUIRED",
        "REPORT_RENDER_ARCHIVE_BLOCKED",
        "SUPPORTABILITY_DEGRADED",
        "HOUSE_VIEW_IMPACT_REVIEW",
        "CLIENT_MEETING_PREPARATION",
        "CLIENT_MEETING_PREPARATION",
        "CLIENT_MEETING_PREPARATION",
        "UNSUPPORTED_CAPABILITY",
    ]
    assert all(action.portfolio_id == "PB_SG_GLOBAL_BAL_001" for action in read_model.action_items)


def test_source_read_model_keeps_policy_and_memo_lineage_hashes() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            policy_evaluations=[_policy_evaluation("BLOCKED", "policy_eval_sg_blocked")],
            memos=[
                _memo(memo_status="PENDING_REVIEW", memo_id="memo_sg_review"),
                _memo(
                    memo_status="READY",
                    lifecycle_status="DRAFT",
                    memo_id="memo_sg_draft",
                ),
            ],
        )
    )

    policy_action = next(
        action
        for action in read_model.action_items
        if action.action_family == "POLICY_REVIEW_REQUIRED"
    )
    memo_action = next(
        action
        for action in read_model.action_items
        if action.action_family == "MEMO_PACKAGE_BLOCKED" and action.memo_id == "memo_sg_review"
    )

    assert policy_action.status == "BLOCKED"
    assert policy_action.lineage_refs[0].lineage_id == "policy_evaluation:policy_eval_sg_blocked"
    assert policy_action.lineage_refs[0].content_hash == "sha256:policy_eval_sg_blocked"
    assert memo_action.reason_codes == ["MEMO_REVIEW_REQUIRED", "CLIENT_READY_BLOCKED"]
    assert memo_action.lineage_refs[0].lineage_id == "proposal_memo:memo_sg_review"
    assert memo_action.lineage_refs[0].content_hash == "sha256:memo_sg_review"
    assert any(
        action.reason_codes == ["MEMO_FINALIZATION_REQUIRED", "CLIENT_READY_BLOCKED"]
        for action in read_model.action_items
    )


def test_source_read_model_suppresses_completed_approval_dependencies() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[_proposal("COMPLIANCE_REVIEW")],
            approvals=[
                _approval(
                    proposal_id="proposal_sg_001",
                    approval_type="COMPLIANCE",
                    approved=True,
                )
            ],
        )
    )

    assert read_model.approval_dependencies == []
    assert not any(
        action.action_family == "APPROVAL_DEPENDENCY_AGING" for action in read_model.action_items
    )


def test_source_read_model_marks_rejected_approval_dependency_blocked() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[_proposal("RISK_REVIEW")],
            approvals=[
                _approval(
                    proposal_id="proposal_sg_001",
                    approval_type="RISK",
                    approved=False,
                    approval_id="approval_sg_rejected",
                )
            ],
        )
    )

    action = next(
        action
        for action in read_model.action_items
        if action.action_family == "APPROVAL_DEPENDENCY_AGING"
    )

    assert action.status == "BLOCKED"
    assert action.priority == "CRITICAL"
    assert action.owner_role == "INVESTMENT_DESK"
    assert action.reason_codes == ["RISK_APPROVAL_REJECTED", "CLIENT_READY_BLOCKED"]


def test_source_read_model_does_not_create_actions_for_completed_sources() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[_proposal("EXECUTED")],
            policy_evaluations=[_policy_evaluation("READY")],
            memos=[
                _memo(
                    memo_status="READY",
                    review_events=[{"event_type": "MEMO_REVIEW_RECORDED"}],
                    report_events=[{"event_type": "MEMO_REPORT_PACKAGE_REQUESTED"}],
                    archive_refs=[{"archive_ref": "archive_sg_001"}],
                )
            ],
        )
    )

    assert read_model.policy_reviews == []
    assert read_model.memo_blocks == []
    assert read_model.meeting_preparations == []
    assert read_model.action_items == []
