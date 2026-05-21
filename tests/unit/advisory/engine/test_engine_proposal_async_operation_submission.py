from datetime import datetime, timezone

from src.core.proposals.async_operation_submission import (
    persist_create_proposal_async_submission,
    persist_create_version_async_submission,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 21, 23, 0, tzinfo=timezone.utc)


def _operation(
    *,
    operation_id: str,
    operation_type: str = "CREATE_PROPOSAL",
    idempotency_key: str | None = "idem_async_submit",
    correlation_id: str = "corr_async_submit",
    proposal_id: str | None = None,
    submission_hash: str = "sha256:submission",
) -> ProposalAsyncOperationRecord:
    payload_json = {
        "payload": {"created_by": "advisor_async_submit"},
        "submission_hash": submission_hash,
    }
    if idempotency_key is not None:
        payload_json["idempotency_key"] = idempotency_key
    if proposal_id is not None:
        payload_json["proposal_id"] = proposal_id

    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type=operation_type,
        status="PENDING",
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        proposal_id=proposal_id,
        created_by="advisor_async_submit",
        created_at=_now(),
        payload_json=payload_json,
        attempt_count=0,
        max_attempts=3,
    )


def test_persist_create_proposal_async_submission_creates_new_operation():
    repository = InMemoryProposalRepository()
    operation = _operation(operation_id="pop_async_submit_1")

    result = persist_create_proposal_async_submission(
        repository=repository,
        operation=operation,
        idempotency_key="idem_async_submit",
        submission_hash="sha256:submission",
    )

    assert result.is_new is True
    assert result.is_conflict is False
    assert result.operation.operation_id == "pop_async_submit_1"
    assert repository.get_operation(operation_id="pop_async_submit_1") is not None


def test_persist_create_proposal_async_submission_replays_matching_idempotency_key():
    repository = InMemoryProposalRepository()
    original = _operation(operation_id="pop_async_submit_original")
    replay = _operation(operation_id="pop_async_submit_replay")
    repository.create_operation(original)

    result = persist_create_proposal_async_submission(
        repository=repository,
        operation=replay,
        idempotency_key="idem_async_submit",
        submission_hash="sha256:submission",
    )

    assert result.is_new is False
    assert result.is_conflict is False
    assert result.operation.operation_id == "pop_async_submit_original"
    assert repository.get_operation(operation_id="pop_async_submit_replay") is None


def test_persist_create_proposal_async_submission_reports_hash_conflict():
    repository = InMemoryProposalRepository()
    original = _operation(operation_id="pop_async_submit_original")
    replay = _operation(operation_id="pop_async_submit_replay")
    repository.create_operation(original)

    result = persist_create_proposal_async_submission(
        repository=repository,
        operation=replay,
        idempotency_key="idem_async_submit",
        submission_hash="sha256:changed",
    )

    assert result.is_new is False
    assert result.is_conflict is True
    assert result.conflict_message == "IDEMPOTENCY_KEY_CONFLICT: async submission hash mismatch"
    assert result.operation.operation_id == "pop_async_submit_original"


def test_persist_create_version_async_submission_creates_when_correlation_is_unused():
    repository = InMemoryProposalRepository()
    operation = _operation(
        operation_id="pop_async_version_submit_1",
        operation_type="CREATE_PROPOSAL_VERSION",
        idempotency_key=None,
        proposal_id="pp_async_submit",
    )

    result = persist_create_version_async_submission(
        repository=repository,
        existing_operation=None,
        operation=operation,
        proposal_id="pp_async_submit",
        submission_hash="sha256:submission",
    )

    assert result.is_new is True
    assert result.is_conflict is False
    assert repository.get_operation(operation_id="pop_async_version_submit_1") is not None


def test_persist_create_version_async_submission_replays_matching_correlation():
    repository = InMemoryProposalRepository()
    original = _operation(
        operation_id="pop_async_version_submit_original",
        operation_type="CREATE_PROPOSAL_VERSION",
        idempotency_key=None,
        proposal_id="pp_async_submit",
    )
    replay = _operation(
        operation_id="pop_async_version_submit_replay",
        operation_type="CREATE_PROPOSAL_VERSION",
        idempotency_key=None,
        proposal_id="pp_async_submit",
    )

    result = persist_create_version_async_submission(
        repository=repository,
        existing_operation=original,
        operation=replay,
        proposal_id="pp_async_submit",
        submission_hash="sha256:submission",
    )

    assert result.is_new is False
    assert result.is_conflict is False
    assert result.operation.operation_id == "pop_async_version_submit_original"
    assert repository.get_operation(operation_id="pop_async_version_submit_replay") is None


def test_persist_create_version_async_submission_reports_correlation_conflict():
    repository = InMemoryProposalRepository()
    original = _operation(
        operation_id="pop_async_version_submit_original",
        operation_type="CREATE_PROPOSAL_VERSION",
        idempotency_key=None,
        proposal_id="pp_async_submit",
    )
    replay = _operation(
        operation_id="pop_async_version_submit_replay",
        operation_type="CREATE_PROPOSAL_VERSION",
        idempotency_key=None,
        proposal_id="pp_async_submit",
    )

    result = persist_create_version_async_submission(
        repository=repository,
        existing_operation=original,
        operation=replay,
        proposal_id="pp_async_submit",
        submission_hash="sha256:changed",
    )

    assert result.is_new is False
    assert result.is_conflict is True
    assert result.conflict_message == "CORRELATION_ID_CONFLICT: async version submission mismatch"
    assert result.operation.operation_id == "pop_async_version_submit_original"
