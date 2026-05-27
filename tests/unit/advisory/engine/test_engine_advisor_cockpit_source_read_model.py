from __future__ import annotations

from datetime import UTC, datetime

from src.core.advisor_cockpit import (
    ACTIVE_PROPOSAL_STATES,
    COCKPIT_POLICY_REVIEW_STATUSES,
    FOLLOW_UP_PROPOSAL_STATES,
    AdvisorCockpitSourceBatch,
    AdvisorCockpitSourceReadModel,
    SupportabilityDegradedActionSource,
    UnsupportedCapabilityActionSource,
    build_advisor_cockpit_source_read_model,
)
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord

AS_OF = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)


def test_source_read_model_exports_cockpit_source_filters() -> None:
    assert "COMPLIANCE_REVIEW" in ACTIVE_PROPOSAL_STATES
    assert "EXECUTED" not in ACTIVE_PROPOSAL_STATES
    assert FOLLOW_UP_PROPOSAL_STATES == frozenset({"AWAITING_CLIENT_CONSENT"})
    assert COCKPIT_POLICY_REVIEW_STATUSES == frozenset({"PENDING_REVIEW", "BLOCKED"})


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
    )


def test_source_read_model_maps_preloaded_sources_to_sorted_cockpit_actions() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[
                _proposal("COMPLIANCE_REVIEW", proposal_id="proposal_sg_001"),
                _proposal("AWAITING_CLIENT_CONSENT", proposal_id="proposal_sg_consent"),
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
        "proposals": 3,
        "policy_evaluations": 2,
        "memos": 2,
        "supportability_events": 1,
        "unsupported_capabilities": 1,
    }
    assert [source.policy_evaluation_id for source in read_model.policy_reviews] == [
        "policy_eval_sg_pending"
    ]
    assert [source.memo_id for source in read_model.memo_blocks] == ["memo_sg_blocked"]
    assert [source.proposal_id for source in read_model.meeting_preparations] == [
        "proposal_sg_001",
        "proposal_sg_consent",
    ]
    assert [source.proposal_id for source in read_model.client_follow_ups] == [
        "proposal_sg_consent"
    ]
    assert [action.action_family for action in read_model.action_items] == [
        "POLICY_REVIEW_REQUIRED",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_FOLLOW_UP_REQUIRED",
        "SUPPORTABILITY_DEGRADED",
        "CLIENT_MEETING_PREPARATION",
        "CLIENT_MEETING_PREPARATION",
        "UNSUPPORTED_CAPABILITY",
    ]


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


def test_source_read_model_does_not_create_actions_for_completed_sources() -> None:
    read_model = build_advisor_cockpit_source_read_model(
        AdvisorCockpitSourceBatch(
            proposals=[_proposal("EXECUTED")],
            policy_evaluations=[_policy_evaluation("READY")],
            memos=[
                _memo(
                    memo_status="READY",
                    review_events=[{"event_type": "MEMO_REVIEW_RECORDED"}],
                )
            ],
        )
    )

    assert read_model.policy_reviews == []
    assert read_model.memo_blocks == []
    assert read_model.meeting_preparations == []
    assert read_model.action_items == []
