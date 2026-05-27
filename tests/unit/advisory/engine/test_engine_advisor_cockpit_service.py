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
        self.bulk_approval_reads = 0
        self.per_proposal_memo_reads = 0
        self.per_proposal_approval_reads = 0

    def list_memos(self, *, proposal_id: str) -> list[ProposalMemoRecord]:
        self.per_proposal_memo_reads += 1
        return super().list_memos(proposal_id=proposal_id)

    def list_memos_for_proposals(self, *, proposal_ids: list[str]) -> list[ProposalMemoRecord]:
        self.bulk_memo_reads += 1
        return super().list_memos_for_proposals(proposal_ids=proposal_ids)

    def list_approvals(self, *, proposal_id: str):
        self.per_proposal_approval_reads += 1
        return super().list_approvals(proposal_id=proposal_id)

    def list_approvals_for_proposals(self, *, proposal_ids: list[str]):
        self.bulk_approval_reads += 1
        return super().list_approvals_for_proposals(proposal_ids=proposal_ids)


def _proposal(
    *,
    proposal_id: str = "proposal_sg_001",
    current_version_no: int = 1,
    current_state: str = "COMPLIANCE_REVIEW",
) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        created_by="advisor_sg_001",
        created_at=NOW,
        last_event_at=NOW,
        current_state=current_state,
        current_version_no=current_version_no,
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

    assert page.total_count == 4
    assert [action.action_family for action in page.items] == [
        "POLICY_REVIEW_REQUIRED",
        "APPROVAL_DEPENDENCY_AGING",
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

    assert page.total_count == 4
    assert repository.bulk_memo_reads == 1
    assert repository.bulk_approval_reads == 1
    assert repository.per_proposal_memo_reads == 0
    assert repository.per_proposal_approval_reads == 0


def test_cockpit_service_snapshot_preserves_supported_downstream_posture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)

    snapshot = service.get_snapshot(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        correlation_id=None,
    )

    assert snapshot.action_counts["status.PENDING_REVIEW"] == 2
    assert snapshot.action_counts["status.BLOCKED"] == 1
    assert snapshot.action_counts["family.APPROVAL_DEPENDENCY_AGING"] == 1
    assert [packet.packet_id for packet in snapshot.preparation_packets] == [
        "prep_proposal_sg_001_v1"
    ]
    assert snapshot.preparation_packets[0].context_type == "PROPOSAL"
    assert snapshot.preparation_packets[0].context_ref == "proposal_sg_001"
    assert snapshot.preparation_packets[0].evidence_refs[0].evidence_type == (
        "MEETING_PREPARATION_PACKET"
    )
    assert snapshot.preparation_packets[0].sections[0]["summary"] == (
        "Active advisory proposal is available for meeting preparation."
    )
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


def test_cockpit_service_lists_preparation_packets_with_cursor_and_supportability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = InMemoryProposalRepository()
    repository.create_proposal(_proposal())
    repository.create_proposal(_proposal(proposal_id="proposal_sg_002", current_version_no=2))
    monkeypatch.setattr(cockpit_service, "list_policy_evaluation_records", lambda **_: [])
    service = AdvisorCockpitService(repository=repository, now_fn=lambda: NOW)

    first_page = service.list_preparation_packets(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=1,
        cursor=None,
        correlation_id="corr-prep-001",
    )
    second_page = service.list_preparation_packets(
        caller_context=_caller(),
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        limit=1,
        cursor=first_page.next_cursor,
        correlation_id="corr-prep-001",
    )

    assert first_page.total_count == 2
    assert first_page.page_size == 1
    assert first_page.next_cursor == first_page.items[0].packet_id
    assert {packet.packet_id for packet in first_page.items + second_page.items} == {
        "prep_proposal_sg_001_v1",
        "prep_proposal_sg_002_v2",
    }
    assert second_page.next_cursor is None
    assert first_page.supportability["api_posture"] == "SUPPORTED_BY_LOTUS_ADVISE_RFC0026"
    assert first_page.items[0].sections[0]["source_ref"] in {
        "proposal_sg_001",
        "proposal_sg_002",
    }

    with pytest.raises(
        ProposalValidationError,
        match="ADVISOR_COCKPIT_PREPARATION_CURSOR_INVALID",
    ):
        service.list_preparation_packets(
            caller_context=_caller(),
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            limit=1,
            cursor="missing-preparation-packet",
            correlation_id=None,
        )


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
