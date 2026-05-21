from datetime import datetime, timezone

from src.core.proposals.async_operation_persistence import (
    persist_async_attempt_started,
    persist_async_operation_failed,
    persist_async_operation_succeeded,
    persist_async_runtime_exception_outcome,
)
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateResponse,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalWorkflowEvent,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 22, 0, tzinfo=timezone.utc)


def _operation(*, attempt_count: int = 0, max_attempts: int = 3) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id="pop_async_persist",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_async_persist",
        idempotency_key="idem_async_persist",
        proposal_id=None,
        created_by="advisor_async_persist",
        created_at=_now(),
        payload_json={"payload": {"created_by": "advisor_async_persist"}},
        attempt_count=attempt_count,
        max_attempts=max_attempts,
    )


def _response() -> ProposalCreateResponse:
    return ProposalCreateResponse.model_construct(
        proposal=ProposalSummary(
            proposal_id="pp_async_persist",
            portfolio_id="pf_async_persist",
            mandate_id="mandate_async_persist",
            jurisdiction="SG",
            created_by="advisor_async_persist",
            created_at="2026-05-21T22:00:00+00:00",
            last_event_at="2026-05-21T22:01:00+00:00",
            current_state="DRAFT",
            current_version_no=1,
            title="Async persistence proposal",
            lifecycle_origin="DIRECT_CREATE",
            source_workspace_id=None,
        ),
        version=ProposalVersionDetail.model_construct(
            proposal_version_id="ppv_async_persist",
            proposal_id="pp_async_persist",
            version_no=1,
            created_at="2026-05-21T22:01:00+00:00",
            request_hash="sha256:req",
            artifact_hash="sha256:artifact",
            simulation_hash="sha256:simulation",
            status_at_creation="READY",
            proposal_result={"status": "READY"},
            artifact={},
            evidence_bundle={},
            gate_decision=None,
        ),
        latest_workflow_event=ProposalWorkflowEvent(
            event_id="pwe_async_persist",
            proposal_id="pp_async_persist",
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id="advisor_async_persist",
            occurred_at="2026-05-21T22:01:00+00:00",
            reason={},
            related_version_no=1,
        ),
    )


def _stored_operation() -> tuple[InMemoryProposalRepository, ProposalAsyncOperationRecord]:
    repository = InMemoryProposalRepository()
    operation = _operation()
    repository.create_operation(operation)
    return repository, operation


def test_persist_async_attempt_started_updates_running_lease():
    repository, operation = _stored_operation()

    persist_async_attempt_started(
        repository=repository,
        operation=operation,
        attempt_started_at=_now(),
        lease_seconds=60,
    )

    stored = repository.get_operation(operation_id="pop_async_persist")
    assert stored is not None
    assert stored.status == "RUNNING"
    assert stored.attempt_count == 1
    assert stored.lease_expires_at is not None


def test_persist_async_operation_succeeded_stores_result_and_terminal_state():
    repository, operation = _stored_operation()

    persist_async_operation_succeeded(
        repository=repository,
        operation=operation,
        response=_response(),
        finished_at=_now(),
    )

    stored = repository.get_operation(operation_id="pop_async_persist")
    assert stored is not None
    assert stored.status == "SUCCEEDED"
    assert stored.proposal_id == "pp_async_persist"
    assert stored.result_json is not None
    assert stored.error_json is None


def test_persist_async_operation_failed_stores_terminal_error():
    repository, operation = _stored_operation()

    persist_async_operation_failed(
        repository=repository,
        operation=operation,
        code="ProposalValidationError",
        message="invalid proposal",
        finished_at=_now(),
    )

    stored = repository.get_operation(operation_id="pop_async_persist")
    assert stored is not None
    assert stored.status == "FAILED"
    assert stored.error_json == {
        "code": "ProposalValidationError",
        "message": "invalid proposal",
    }


def test_persist_async_runtime_exception_outcome_requeues_until_attempts_exhausted():
    repository, operation = _stored_operation()
    operation.attempt_count = 1
    operation.max_attempts = 2

    should_requeue = persist_async_runtime_exception_outcome(
        repository=repository,
        operation=operation,
        exc=RuntimeError("temporary failure"),
        finished_at=_now(),
    )

    assert should_requeue is True
    stored = repository.get_operation(operation_id="pop_async_persist")
    assert stored is not None
    assert stored.status == "PENDING"
    assert stored.finished_at is None

    operation.attempt_count = 2
    should_requeue = persist_async_runtime_exception_outcome(
        repository=repository,
        operation=operation,
        exc=RuntimeError("final failure"),
        finished_at=_now(),
    )

    assert should_requeue is False
    stored = repository.get_operation(operation_id="pop_async_persist")
    assert stored is not None
    assert stored.status == "FAILED"
    assert stored.finished_at == _now()
