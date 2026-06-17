from datetime import datetime, timezone

from src.core.proposals.async_operation_runner import run_async_operation_until_terminal
from src.core.proposals.exceptions import ProposalLifecycleError
from src.core.proposals.models import (
    ProposalAsyncOperationRecord,
    ProposalCreateResponse,
    ProposalSummary,
    ProposalVersionDetail,
    ProposalWorkflowEvent,
)
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc)


def _operation(
    *,
    operation_id: str = "pop_runner",
    attempt_count: int = 0,
    max_attempts: int = 3,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id=f"corr_{operation_id}",
        idempotency_key=f"idem_{operation_id}",
        proposal_id=None,
        created_by="advisor_runner",
        created_at=_now(),
        payload_json={"payload": {"created_by": "advisor_runner"}},
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )


def _response() -> ProposalCreateResponse:
    return ProposalCreateResponse.model_construct(
        proposal=ProposalSummary(
            proposal_id="pp_runner",
            portfolio_id="pf_runner",
            mandate_id="mandate_runner",
            jurisdiction="SG",
            created_by="advisor_runner",
            created_at="2026-05-22T09:00:00+00:00",
            last_event_at="2026-05-22T09:01:00+00:00",
            current_state="DRAFT",
            current_version_no=1,
            title="Async runner proposal",
            lifecycle_origin="DIRECT_CREATE",
            source_workspace_id=None,
        ),
        version=ProposalVersionDetail.model_construct(
            proposal_version_id="ppv_runner",
            proposal_id="pp_runner",
            version_no=1,
            created_at="2026-05-22T09:01:00+00:00",
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
            event_id="pwe_runner",
            proposal_id="pp_runner",
            event_type="CREATED",
            from_state=None,
            to_state="DRAFT",
            actor_id="advisor_runner",
            occurred_at="2026-05-22T09:01:00+00:00",
            reason={},
            related_version_no=1,
        ),
    )


def test_async_operation_runner_retries_transient_runtime_exception_until_success():
    repository = InMemoryProposalRepository()
    operation = _operation(operation_id="pop_retry_success", max_attempts=3)
    repository.create_operation(operation)
    executor_calls = 0

    def executor() -> ProposalCreateResponse:
        nonlocal executor_calls
        executor_calls += 1
        if executor_calls == 1:
            raise RuntimeError("temporary dependency failure")
        return _response()

    run_async_operation_until_terminal(
        repository=repository,
        operation_id="pop_retry_success",
        executor=executor,
        utc_now=_now,
    )

    stored = repository.get_operation(operation_id="pop_retry_success")
    assert stored is not None
    assert executor_calls == 2
    assert stored.status == "SUCCEEDED"
    assert stored.attempt_count == 2
    assert stored.proposal_id == "pp_runner"
    assert stored.error_json is None
    assert stored.lease_expires_at is None


def test_async_operation_runner_fails_exhausted_operation_without_extra_attempt():
    repository = InMemoryProposalRepository()
    operation = _operation(operation_id="pop_exhausted", attempt_count=3, max_attempts=3)
    repository.create_operation(operation)
    executor_calls = 0

    def executor() -> ProposalCreateResponse:
        nonlocal executor_calls
        executor_calls += 1
        raise AssertionError("exhausted operation should not execute")

    run_async_operation_until_terminal(
        repository=repository,
        operation_id="pop_exhausted",
        executor=executor,
        utc_now=_now,
    )

    stored = repository.get_operation(operation_id="pop_exhausted")
    assert stored is not None
    assert executor_calls == 0
    assert stored.status == "FAILED"
    assert stored.attempt_count == 3
    assert stored.error_json == {
        "code": "ProposalLifecycleError",
        "message": "PROPOSAL_ASYNC_ATTEMPTS_EXHAUSTED",
    }
    assert stored.finished_at == _now()


def test_async_operation_runner_records_lifecycle_error_as_terminal_failure():
    repository = InMemoryProposalRepository()
    operation = _operation(operation_id="pop_lifecycle_failure", max_attempts=3)
    repository.create_operation(operation)
    executor_calls = 0

    def executor() -> ProposalCreateResponse:
        nonlocal executor_calls
        executor_calls += 1
        raise ProposalLifecycleError("PROPOSAL_CONTEXT_RESOLUTION_FAILED")

    run_async_operation_until_terminal(
        repository=repository,
        operation_id="pop_lifecycle_failure",
        executor=executor,
        utc_now=_now,
    )

    stored = repository.get_operation(operation_id="pop_lifecycle_failure")
    assert stored is not None
    assert executor_calls == 1
    assert stored.status == "FAILED"
    assert stored.attempt_count == 1
    assert stored.error_json == {
        "code": "ProposalLifecycleError",
        "message": "PROPOSAL_CONTEXT_RESOLUTION_FAILED",
    }
    assert stored.finished_at == _now()
    assert stored.lease_expires_at is None


def test_async_operation_runner_returns_without_executing_when_operation_is_missing():
    repository = InMemoryProposalRepository()
    executor_calls = 0

    def executor() -> ProposalCreateResponse:
        nonlocal executor_calls
        executor_calls += 1
        raise AssertionError("missing operation should not execute")

    run_async_operation_until_terminal(
        repository=repository,
        operation_id="pop_missing",
        executor=executor,
        utc_now=_now,
    )

    assert executor_calls == 0
    assert repository.get_operation(operation_id="pop_missing") is None
