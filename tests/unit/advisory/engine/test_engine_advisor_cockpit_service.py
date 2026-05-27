from __future__ import annotations

from datetime import UTC, datetime

import pytest

import src.core.advisor_cockpit.service as cockpit_service
from src.core.advisor_cockpit import (
    AdvisorCockpitAcknowledgeRequest,
    AdvisorCockpitService,
    CockpitCallerContext,
)
from src.core.policy_packs.models import PolicyEvaluationRecord
from src.core.proposals.exceptions import ProposalIdempotencyConflictError, ProposalValidationError
from src.core.proposals.models import ProposalMemoRecord, ProposalRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository

NOW = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)


class CountingCockpitRepository(InMemoryProposalRepository):
    def __init__(self) -> None:
        super().__init__()
        self.bulk_memo_reads = 0
        self.per_proposal_memo_reads = 0

    def list_memos(self, *, proposal_id: str) -> list[ProposalMemoRecord]:
        self.per_proposal_memo_reads += 1
        return super().list_memos(proposal_id=proposal_id)

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]:
        self.bulk_memo_reads += 1
        return super().list_memos_for_proposals(proposal_ids=proposal_ids)


def _proposal() -> ProposalRecord:
    return ProposalRecord(
        proposal_id="proposal_sg_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        created_by="advisor_sg_001",
        created_at=NOW,
        last_event_at=NOW,
        current_state="COMPLIANCE_REVIEW",
        current_version_no=1,
        title="Singapore global balanced proposal",
    )


def _memo() -> ProposalMemoRecord:
    return ProposalMemoRecord(
        memo_id="memo_sg_001",
        proposal_id="proposal_sg_001",
        proposal_version_no=1,
        memo_version="advisory-proposal-memo-evidence-pack.v1",
        memo_status="BLOCKED",
        lifecycle_status="FINALIZED",
        created_by="advisor_sg_001",
        created_at=NOW,
        source_input_hash="sha256:memo-source",
        memo_hash="sha256:memo",
        memo_json={"memo_id": "memo_sg_001"},
    )


def _policy() -> PolicyEvaluationRecord:
    return PolicyEvaluationRecord(
        evaluation_id="policy_eval_sg_001",
        proposal_id="proposal_sg_001",
        proposal_version_id="ppv_sg_001",
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        policy_pack_id="SG_PRIVATE_BANKING_REFERENCE",
        policy_version="2026.05",
        generated_at="2026-05-27T08:00:00+00:00",
        created_by="advisor_sg_001",
        evaluation_status="PENDING_REVIEW",
        policy_content_hash="sha256:policy-content",
        source_evidence_hash="sha256:source-evidence",
        evaluation_hash="sha256:policy-evaluation",
        evaluation_json={"evaluation_status": "PENDING_REVIEW"},
    )


def _service(monkeypatch: pytest.MonkeyPatch) -> AdvisorCockpitService:
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_memo(_memo())
    monkeypatch.setattr(
        cockpit_service,
        "list_policy_evaluation_records",
        lambda **_: [_policy()],
    )
    return AdvisorCockpitService(repository=repository, now_fn=lambda: NOW)


def _caller() -> CockpitCallerContext:
    return CockpitCallerContext(advisor_id="advisor_sg_001", role="ADVISOR")


def test_cockpit_service_lists_source_backed_actions_with_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)

    page = service.list_actions(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=25,
        cursor=None,
        correlation_id="corr-cockpit-001",
    )

    assert page.total_count == 3
    assert [action.action_family for action in page.items] == [
        "POLICY_REVIEW_REQUIRED",
        "MEMO_PACKAGE_BLOCKED",
        "CLIENT_MEETING_PREPARATION",
    ]
    assert all(action.correlation_id == "corr-cockpit-001" for action in page.items)


def test_cockpit_service_batches_memo_source_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = CountingCockpitRepository()
    repository.create_proposal(_proposal())
    repository.create_memo(_memo())
    monkeypatch.setattr(
        cockpit_service,
        "list_policy_evaluation_records",
        lambda **_: [_policy()],
    )
    service = AdvisorCockpitService(repository=repository, now_fn=lambda: NOW)

    page = service.list_actions(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=25,
        cursor=None,
        correlation_id=None,
    )

    assert page.total_count == 3
    assert repository.bulk_memo_reads == 1
    assert repository.per_proposal_memo_reads == 0


def test_cockpit_service_snapshot_preserves_supported_downstream_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)

    snapshot = service.get_snapshot(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        correlation_id=None,
    )

    assert snapshot.action_counts["status.PENDING_REVIEW"] == 1
    assert snapshot.action_counts["status.BLOCKED"] == 1
    assert snapshot.supportability["gateway_posture"] == "SUPPORTED_BY_LOTUS_GATEWAY_RFC0026"
    assert snapshot.supportability["workbench_posture"] == (
        "CANONICAL_WORKBENCH_PROOF_PASSED_RFC0026"
    )
    assert snapshot.supportability["data_product_posture"] == (
        "ACTIVE_ADVISOR_COCKPIT_PRODUCTS_RFC0026"
    )
    assert snapshot.supportability["canonical_proof"] == (
        "PB_SG_GLOBAL_BAL_001_ADVISOR_COCKPIT_VALIDATED"
    )
    assert snapshot.supportability["client_ready_publication"] == "BLOCKED"
    supportability = service.get_supportability(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        correlation_id=None,
    )
    assert supportability.posture == "ADVISE_GATEWAY_WORKBENCH_CANONICAL_PROOF_SUPPORTED"


def test_cockpit_acknowledgement_is_idempotent_and_does_not_clear_blocking_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)
    action = service.list_actions(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=25,
        cursor=None,
        correlation_id=None,
    ).items[0]
    payload = AdvisorCockpitAcknowledgeRequest(
        action_item_version=action.action_item_version,
        acknowledged_by="advisor_sg_001",
        acknowledgement_note="Reviewed pending policy action.",
    )

    response = service.acknowledge_action(
        action_item_id=action.action_item_id,
        payload=payload,
        idempotency_key="ack-policy-001",
        correlation_id="corr-ack-001",
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )
    replay = service.acknowledge_action(
        action_item_id=action.action_item_id,
        payload=payload,
        idempotency_key="ack-policy-001",
        correlation_id="corr-ack-001",
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )

    assert response.replayed is False
    assert replay.replayed is True
    assert replay.action_item.status == "PENDING_REVIEW"
    assert replay.action_item.acknowledgement_state.acknowledged is True


def test_cockpit_acknowledgement_rejects_conflict_and_stale_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)
    action = service.list_actions(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=25,
        cursor=None,
        correlation_id=None,
    ).items[0]
    payload = AdvisorCockpitAcknowledgeRequest(
        action_item_version=action.action_item_version,
        acknowledged_by="advisor_sg_001",
    )
    service.acknowledge_action(
        action_item_id=action.action_item_id,
        payload=payload,
        idempotency_key="ack-conflict-001",
        correlation_id="corr-ack-001",
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
    )

    with pytest.raises(ProposalIdempotencyConflictError):
        service.acknowledge_action(
            action_item_id=action.action_item_id,
            payload=payload,
            idempotency_key="ack-conflict-001",
            correlation_id="corr-ack-different",
            caller_context=_caller(),
            portfolio_id="PB_SG_GLOBAL_BAL_001",
        )

    with pytest.raises(ProposalValidationError, match="ADVISOR_COCKPIT_ACTION_VERSION_STALE"):
        service.acknowledge_action(
            action_item_id=action.action_item_id,
            payload=AdvisorCockpitAcknowledgeRequest(
                action_item_version=99,
                acknowledged_by="advisor_sg_001",
            ),
            idempotency_key="ack-stale-001",
            correlation_id=None,
            caller_context=_caller(),
            portfolio_id="PB_SG_GLOBAL_BAL_001",
        )
