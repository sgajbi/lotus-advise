from datetime import datetime, timezone

from src.core.proposals.async_operation_runner import run_async_operation_until_terminal
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 22, 9, 0, tzinfo=timezone.utc)


def test_async_operation_runner_fails_exhausted_operation_without_extra_attempt():
    repository = InMemoryProposalRepository()
    operation = ProposalAsyncOperationRecord(
        operation_id="pop_exhausted",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_exhausted",
        idempotency_key="idem_exhausted",
        proposal_id=None,
        created_by="advisor_exhausted",
        created_at=_now(),
        payload_json={"payload": {"created_by": "advisor_exhausted"}},
        attempt_count=3,
        max_attempts=3,
        started_at=None,
        lease_expires_at=None,
        finished_at=None,
        result_json=None,
        error_json=None,
    )
    repository.create_operation(operation)
    executor_calls = 0

    def executor():
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


def test_async_operation_runner_returns_without_executing_when_operation_is_missing():
    repository = InMemoryProposalRepository()
    executor_calls = 0

    def executor():
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
