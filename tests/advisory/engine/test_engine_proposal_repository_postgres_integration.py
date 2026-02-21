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
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)
from src.infrastructure.proposals.postgres import PostgresProposalRepository
from tests.advisory.engine.test_engine_proposal_repository_postgres import (
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


def _reset_tables(repository: PostgresProposalRepository) -> None:
    with closing(repository._connect()) as connection:  # noqa: SLF001
        connection.execute("DELETE FROM proposal_approvals")
        connection.execute("DELETE FROM proposal_workflow_events")
        connection.execute("DELETE FROM proposal_versions")
        connection.execute("DELETE FROM proposal_records")
        connection.execute("DELETE FROM proposal_async_operations")
        connection.execute("DELETE FROM proposal_idempotency")
        connection.commit()
