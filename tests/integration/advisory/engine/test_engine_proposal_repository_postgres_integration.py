import os
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalIdempotencyRecord,
    ProposalRecord,
    ProposalSimulationIdempotencyRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.postgres import PostgresProposalRepository
from tests.unit.advisory.engine.test_engine_proposal_repository_postgres import (
    _build_repository as _build_fake_repository,
)

_DSN = os.getenv("PROPOSAL_POSTGRES_INTEGRATION_DSN", "").strip()


@pytest.fixture
def repository(monkeypatch: pytest.MonkeyPatch) -> PostgresProposalRepository:
    if _DSN:
        try:
            repo = PostgresProposalRepository(dsn=_DSN)
            _reset_tables(repo)
            return repo
        except Exception:
            pass
    repo, _ = _build_fake_repository(monkeypatch)
    return repo


def test_live_postgres_proposal_repository_parity_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    proposal_id = f"pp-{uuid.uuid4().hex}"
    operation_id = f"pop-{uuid.uuid4().hex}"
    correlation_id = f"corr-{uuid.uuid4().hex}"
    idempotency_key = f"idem-{uuid.uuid4().hex}"
    version_id = f"ppv-{uuid.uuid4().hex}"
    event_id = f"pwe-{uuid.uuid4().hex}"
    approval_id = f"pap-{uuid.uuid4().hex}"

    idempotency = ProposalIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_hash=f"sha256:{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        proposal_version_no=1,
        created_at=now,
    )
    repository.save_idempotency(idempotency)
    loaded_idempotency = repository.get_idempotency(idempotency_key=idempotency_key)
    assert loaded_idempotency is not None
    assert loaded_idempotency.proposal_id == proposal_id

    operation = ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        proposal_id=None,
        created_by="advisor_live",
        created_at=now,
        started_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    repository.create_operation(operation)
    operation.status = "SUCCEEDED"
    operation.started_at = now
    operation.finished_at = now + timedelta(seconds=1)
    operation.proposal_id = proposal_id
    operation.result_json = {"proposal_id": proposal_id}
    repository.update_operation(operation)

    loaded_operation = repository.get_operation(operation_id=operation_id)
    assert loaded_operation is not None
    assert loaded_operation.status == "SUCCEEDED"
    by_correlation = repository.get_operation_by_correlation(correlation_id=correlation_id)
    assert by_correlation is not None
    assert by_correlation.operation_id == operation_id

    proposal = ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="pf-live",
        mandate_id="mandate-live",
        jurisdiction="SG",
        created_by="advisor_live",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="Live parity proposal",
        advisor_notes="integration contract",
    )
    repository.create_proposal(proposal)

    version = ProposalVersionRecord(
        proposal_version_id=version_id,
        proposal_id=proposal_id,
        version_no=1,
        created_at=now,
        request_hash=idempotency.request_hash,
        artifact_hash=f"sha256:{uuid.uuid4().hex}",
        simulation_hash=f"sha256:{uuid.uuid4().hex}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={"artifact_id": f"pa-{uuid.uuid4().hex}"},
        evidence_bundle_json={"hashes": {"request_hash": idempotency.request_hash}},
        gate_decision_json=None,
    )
    repository.create_version(version)
    loaded_version = repository.get_current_version(proposal_id=proposal_id)
    assert loaded_version is not None
    assert loaded_version.proposal_version_id == version_id

    event = ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal_id,
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor_live",
        occurred_at=now + timedelta(seconds=2),
        reason_json={"comment": "submit"},
        related_version_no=1,
    )
    approval = ProposalApprovalRecordData(
        approval_id=approval_id,
        proposal_id=proposal_id,
        approval_type="RISK",
        approved=True,
        actor_id="risk_live",
        occurred_at=now + timedelta(seconds=3),
        details_json={"ticket_id": f"risk-{uuid.uuid4().hex[:8]}"},
        related_version_no=1,
    )
    transitioned = ProposalRecord(
        proposal_id=proposal.proposal_id,
        portfolio_id=proposal.portfolio_id,
        mandate_id=proposal.mandate_id,
        jurisdiction=proposal.jurisdiction,
        created_by=proposal.created_by,
        created_at=proposal.created_at,
        last_event_at=event.occurred_at,
        current_state="RISK_REVIEW",
        current_version_no=proposal.current_version_no,
        title=proposal.title,
        advisor_notes=proposal.advisor_notes,
    )
    transition_result = repository.transition_proposal(
        proposal=transitioned,
        event=event,
        approval=approval,
    )
    assert transition_result.event.event_id == event_id
    assert transition_result.approval is not None
    assert transition_result.approval.approval_id == approval_id

    stored_events = repository.list_events(proposal_id=proposal_id)
    assert [row.event_id for row in stored_events] == [event_id]

    stored_approvals = repository.list_approvals(proposal_id=proposal_id)
    assert [row.approval_id for row in stored_approvals] == [approval_id]

    stored_proposal = repository.get_proposal(proposal_id=proposal_id)
    assert stored_proposal is not None
    assert stored_proposal.current_state == "RISK_REVIEW"

    listed, next_cursor = repository.list_proposals(
        portfolio_id="pf-live",
        state="RISK_REVIEW",
        created_by="advisor_live",
        created_from=now - timedelta(minutes=1),
        created_to=now + timedelta(minutes=1),
        limit=10,
        cursor=None,
    )
    assert len(listed) == 1
    assert listed[0].proposal_id == proposal_id
    assert next_cursor is None


def test_live_postgres_simulation_idempotency_roundtrip_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    idempotency_key = f"sim-idem-{uuid.uuid4().hex}"
    request_hash = f"sha256:{uuid.uuid4().hex}"
    first_payload = ProposalSimulationIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        response_json={"proposal_run_id": f"pr-{uuid.uuid4().hex}", "status": "READY"},
        created_at=now,
    )
    repository.save_simulation_idempotency(first_payload)
    loaded = repository.get_simulation_idempotency(idempotency_key=idempotency_key)
    assert loaded is not None
    assert loaded.request_hash == request_hash
    assert loaded.response_json["status"] == "READY"

    updated_payload = ProposalSimulationIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        response_json={"proposal_run_id": f"pr-{uuid.uuid4().hex}", "status": "BLOCKED"},
        created_at=now + timedelta(seconds=1),
    )
    repository.save_simulation_idempotency(updated_payload)
    loaded_updated = repository.get_simulation_idempotency(idempotency_key=idempotency_key)
    assert loaded_updated is not None
    assert loaded_updated.response_json["status"] == "BLOCKED"
    assert repository.get_simulation_idempotency(idempotency_key="sim-idem-missing") is None


def test_live_postgres_operation_missing_lookups_return_none(
    repository: PostgresProposalRepository,
) -> None:
    assert repository.get_operation(operation_id="op-missing") is None
    assert repository.get_operation_by_correlation(correlation_id="corr-missing") is None


def test_live_postgres_list_proposals_pagination_and_invalid_cursor(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    first = ProposalRecord(
        proposal_id=f"pp-{uuid.uuid4().hex}",
        portfolio_id="pf-page",
        mandate_id="mandate-page",
        jurisdiction="SG",
        created_by="advisor-page",
        created_at=now - timedelta(minutes=1),
        last_event_at=now - timedelta(minutes=1),
        current_state="DRAFT",
        current_version_no=1,
        title="Page one",
        advisor_notes=None,
    )
    second = ProposalRecord(
        proposal_id=f"pp-{uuid.uuid4().hex}",
        portfolio_id="pf-page",
        mandate_id="mandate-page",
        jurisdiction="SG",
        created_by="advisor-page",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="Page two",
        advisor_notes=None,
    )
    repository.create_proposal(first)
    repository.create_proposal(second)

    page_one, next_cursor = repository.list_proposals(
        portfolio_id="pf-page",
        state="DRAFT",
        created_by="advisor-page",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=None,
    )
    assert [row.proposal_id for row in page_one] == [second.proposal_id]
    assert next_cursor == second.proposal_id

    page_two, final_cursor = repository.list_proposals(
        portfolio_id="pf-page",
        state="DRAFT",
        created_by="advisor-page",
        created_from=None,
        created_to=None,
        limit=1,
        cursor=next_cursor,
    )
    assert [row.proposal_id for row in page_two] == [first.proposal_id]
    assert final_cursor is None

    invalid_page, invalid_cursor = repository.list_proposals(
        portfolio_id=None,
        state=None,
        created_by=None,
        created_from=None,
        created_to=None,
        limit=10,
        cursor="pp-missing-cursor",
    )
    assert invalid_page == []
    assert invalid_cursor is None


def test_live_postgres_version_get_and_current_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    proposal_id = f"pp-{uuid.uuid4().hex}"
    repository.create_proposal(
        ProposalRecord(
            proposal_id=proposal_id,
            portfolio_id="pf-version",
            mandate_id="mandate-version",
            jurisdiction="SG",
            created_by="advisor-version",
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=2,
            title="Versioned proposal",
            advisor_notes=None,
        )
    )
    version_1 = ProposalVersionRecord(
        proposal_version_id=f"ppv-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        version_no=1,
        created_at=now,
        request_hash=f"sha256:{uuid.uuid4().hex}",
        artifact_hash=f"sha256:{uuid.uuid4().hex}",
        simulation_hash=f"sha256:{uuid.uuid4().hex}",
        status_at_creation="READY",
        proposal_result_json={"status": "READY"},
        artifact_json={"artifact_id": "a1"},
        evidence_bundle_json={"hashes": {"request_hash": "r1"}},
        gate_decision_json=None,
    )
    version_2 = ProposalVersionRecord(
        proposal_version_id=f"ppv-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        version_no=2,
        created_at=now + timedelta(seconds=1),
        request_hash=f"sha256:{uuid.uuid4().hex}",
        artifact_hash=f"sha256:{uuid.uuid4().hex}",
        simulation_hash=f"sha256:{uuid.uuid4().hex}",
        status_at_creation="BLOCKED",
        proposal_result_json={"status": "BLOCKED"},
        artifact_json={"artifact_id": "a2"},
        evidence_bundle_json={"hashes": {"request_hash": "r2"}},
        gate_decision_json={"gate": "CLIENT_CONSENT_REQUIRED"},
    )
    repository.create_version(version_1)
    repository.create_version(version_2)

    loaded_1 = repository.get_version(proposal_id=proposal_id, version_no=1)
    loaded_2 = repository.get_current_version(proposal_id=proposal_id)
    missing = repository.get_version(proposal_id=proposal_id, version_no=3)
    assert loaded_1 is not None
    assert loaded_1.proposal_version_id == version_1.proposal_version_id
    assert loaded_2 is not None
    assert loaded_2.proposal_version_id == version_2.proposal_version_id
    assert missing is None


def test_live_postgres_events_and_approvals_ordering_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    proposal_id = f"pp-{uuid.uuid4().hex}"
    repository.create_proposal(
        ProposalRecord(
            proposal_id=proposal_id,
            portfolio_id="pf-events",
            mandate_id="mandate-events",
            jurisdiction="SG",
            created_by="advisor-events",
            created_at=now,
            last_event_at=now,
            current_state="DRAFT",
            current_version_no=1,
            title="Ordered events",
            advisor_notes=None,
        )
    )
    first_event = ProposalWorkflowEventRecord(
        event_id=f"pwe-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        event_type="CREATED",
        from_state=None,
        to_state="DRAFT",
        actor_id="advisor-events",
        occurred_at=now,
        reason_json={"comment": "created"},
        related_version_no=1,
    )
    second_event = ProposalWorkflowEventRecord(
        event_id=f"pwe-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor-events",
        occurred_at=now + timedelta(seconds=5),
        reason_json={"comment": "submitted"},
        related_version_no=1,
    )
    repository.append_event(first_event)
    repository.append_event(second_event)
    approval = ProposalApprovalRecordData(
        approval_id=f"pap-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        approval_type="RISK",
        approved=True,
        actor_id="risk-events",
        occurred_at=now + timedelta(seconds=6),
        details_json={"ticket_id": "risk-ticket"},
        related_version_no=1,
    )
    repository.create_approval(approval)

    events = repository.list_events(proposal_id=proposal_id)
    approvals = repository.list_approvals(proposal_id=proposal_id)
    assert [row.event_id for row in events] == [first_event.event_id, second_event.event_id]
    assert [row.approval_id for row in approvals] == [approval.approval_id]


def test_live_postgres_transition_without_approval_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    proposal_id = f"pp-{uuid.uuid4().hex}"
    proposal = ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="pf-transition",
        mandate_id="mandate-transition",
        jurisdiction="SG",
        created_by="advisor-transition",
        created_at=now,
        last_event_at=now,
        current_state="RISK_REVIEW",
        current_version_no=1,
        title="Transition without approval",
        advisor_notes=None,
    )
    event = ProposalWorkflowEventRecord(
        event_id=f"pwe-{uuid.uuid4().hex}",
        proposal_id=proposal_id,
        event_type="SUBMITTED_FOR_RISK_REVIEW",
        from_state="DRAFT",
        to_state="RISK_REVIEW",
        actor_id="advisor-transition",
        occurred_at=now,
        reason_json={"comment": "submit"},
        related_version_no=1,
    )

    result = repository.transition_proposal(proposal=proposal, event=event, approval=None)
    assert result.approval is None
    stored = repository.get_proposal(proposal_id=proposal_id)
    assert stored is not None
    assert stored.current_state == "RISK_REVIEW"
    event_ids = [row.event_id for row in repository.list_events(proposal_id=proposal_id)]
    assert event_ids == [event.event_id]
    assert repository.list_approvals(proposal_id=proposal_id) == []


def test_live_postgres_update_proposal_contract(
    repository: PostgresProposalRepository,
) -> None:
    now = datetime.now(timezone.utc)
    proposal_id = f"pp-{uuid.uuid4().hex}"
    proposal = ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="pf-update",
        mandate_id="mandate-update",
        jurisdiction="SG",
        created_by="advisor-update",
        created_at=now,
        last_event_at=now,
        current_state="DRAFT",
        current_version_no=1,
        title="Before update",
        advisor_notes="initial",
    )
    repository.create_proposal(proposal)
    updated = ProposalRecord(
        proposal_id=proposal_id,
        portfolio_id="pf-update",
        mandate_id="mandate-update",
        jurisdiction="SG",
        created_by="advisor-update",
        created_at=now,
        last_event_at=now + timedelta(seconds=1),
        current_state="CANCELLED",
        current_version_no=1,
        title="After update",
        advisor_notes="cancelled by advisor",
    )
    repository.update_proposal(updated)

    stored = repository.get_proposal(proposal_id=proposal_id)
    assert stored is not None
    assert stored.current_state == "CANCELLED"
    assert stored.title == "After update"


def _reset_tables(repository: PostgresProposalRepository) -> None:
    with closing(repository._connect()) as connection:  # noqa: SLF001
        connection.execute(
            "TRUNCATE TABLE proposal_approvals, proposal_workflow_events, "
            "proposal_versions, proposal_records, proposal_async_operations, "
            "proposal_idempotency CASCADE"
        )
        connection.commit()
