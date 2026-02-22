from datetime import datetime, timezone

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalTransitionResult,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _proposal(proposal_id: str, created_by: str, state: str = "DRAFT") -> ProposalRecord:
    now = _now()
    return ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="pf_repo",
        mandate_id=None,
        jurisdiction="SG",
        created_by=created_by,
        created_at=now,
        last_event_at=now,
        current_state=state,
        current_version_no=1,
        title="repo test",
    )


def test_repository_idempotency_roundtrip_and_update_proposal():
    repo = InMemoryProposalRepository()
    created_at = _now()
    record = ProposalIdempotencyRecord(
        idempotency_key="idem-repo-1",
        request_hash="sha256:req",
        proposal_id="pp_repo_1",
        proposal_version_no=1,
        created_at=created_at,
    )

    assert repo.get_idempotency(idempotency_key="idem-repo-1") is None
    repo.save_idempotency(record)
    stored = repo.get_idempotency(idempotency_key="idem-repo-1")
    assert stored is not None
    assert stored.request_hash == "sha256:req"

    proposal = _proposal("pp_repo_1", "advisor_repo")
    repo.create_proposal(proposal)
    proposal.current_state = "CANCELLED"
    repo.update_proposal(proposal)
    fetched = repo.get_proposal(proposal_id="pp_repo_1")
    assert fetched is not None
    assert fetched.current_state == "CANCELLED"


def test_repository_list_filters_cursor_events_and_approvals():
    repo = InMemoryProposalRepository()
    first = _proposal("pp_repo_a", "advisor_a")
    second = _proposal("pp_repo_b", "advisor_b", state="EXECUTION_READY")
    repo.create_proposal(first)
    repo.create_proposal(second)

    rows, next_cursor = repo.list_proposals(
        portfolio_id="pf_repo",
        state="DRAFT",
        created_by="advisor_a",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=None,
    )
    assert len(rows) == 1
    assert rows[0].proposal_id == "pp_repo_a"
    assert next_cursor is None

    rows, _ = repo.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=1,
        cursor="pp_repo_b",
    )
    assert len(rows) == 1
    assert rows[0].proposal_id == "pp_repo_a"

    event = ProposalWorkflowEventRecord(
        event_id="pwe_repo_1",
        proposal_id="pp_repo_a",
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id="advisor_a",
        occurred_at=_now(),
        reason_json={},
        related_version_no=1,
    )
    repo.append_event(event)
    assert repo.list_events(proposal_id="pp_repo_a")[0].event_id == "pwe_repo_1"

    approval = ProposalApprovalRecordData(
        approval_id="pap_repo_1",
        proposal_id="pp_repo_a",
        approval_type="RISK",
        approved=True,
        actor_id="risk",
        occurred_at=_now(),
        details_json={"channel": "INTERNAL"},
        related_version_no=1,
    )
    repo.create_approval(approval)
    assert repo.list_approvals(proposal_id="pp_repo_a")[0].approval_id == "pap_repo_1"


def test_repository_versions_and_transition_transaction_path():
    repo = InMemoryProposalRepository()
    proposal = _proposal("pp_repo_txn", "advisor_txn")
    repo.create_proposal(proposal)
    version = ProposalVersionRecord(
        proposal_version_id="ppv_repo_1",
        proposal_id="pp_repo_txn",
        version_no=1,
        created_at=_now(),
        request_hash="sha256:req",
        artifact_hash="sha256:artifact",
        simulation_hash="sha256:sim",
        status_at_creation="READY",
        proposal_result_json={},
        artifact_json={},
        evidence_bundle_json={},
        gate_decision_json=None,
    )
    repo.create_version(version)
    assert repo.get_version(proposal_id="pp_repo_txn", version_no=1) is not None
    assert repo.get_current_version(proposal_id="pp_repo_txn") is not None

    transition_event = ProposalWorkflowEventRecord(
        event_id="pwe_repo_txn",
        proposal_id="pp_repo_txn",
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_txn",
        occurred_at=_now(),
        reason_json={"comment": "submit"},
        related_version_no=1,
    )
    proposal.current_state = "RISK_REVIEW"
    result = repo.transition_proposal(proposal=proposal, event=transition_event, approval=None)
    assert isinstance(result, ProposalTransitionResult)
    assert result.proposal.current_state == "RISK_REVIEW"
    assert result.event.event_id == "pwe_repo_txn"


def test_repository_created_from_to_filters_and_empty_current_version():
    repo = InMemoryProposalRepository()
    now = _now()
    proposal = ProposalRecord(
        proposal_id="pp_repo_date",
        portfolio_id="pf_repo",
        mandate_id=None,
        jurisdiction="SG",
        created_by="advisor_date",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="date filter",
        advisor_notes=None,
    )
    repo.create_proposal(proposal)

    future = now.replace(year=now.year + 1)
    rows, _ = repo.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=future,
        created_to=None,
        limit=10,
        cursor=None,
    )
    assert rows == []

    past = now.replace(year=now.year - 1)
    rows, _ = repo.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=past,
        limit=10,
        cursor=None,
    )
    assert rows == []

    assert repo.get_current_version(proposal_id="pp_repo_date") is None
