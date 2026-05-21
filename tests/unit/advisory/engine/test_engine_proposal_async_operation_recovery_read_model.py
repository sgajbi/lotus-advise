from datetime import datetime, timedelta, timezone

from src.core.proposals.async_operation_recovery_read_model import (
    load_recoverable_async_operation_read_models,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _now() -> datetime:
    return datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc)


def _operation(
    *,
    operation_id: str,
    operation_type: str = "CREATE_PROPOSAL",
    status: str = "PENDING",
    created_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
) -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id=operation_id,
        operation_type=operation_type,
        status=status,
        correlation_id=f"corr_{operation_id}",
        idempotency_key=f"idem_{operation_id}" if operation_type == "CREATE_PROPOSAL" else None,
        proposal_id="pp_recoverable" if operation_type == "CREATE_PROPOSAL_VERSION" else None,
        created_by="advisor_recovery",
        created_at=created_at or _now(),
        payload_json={"payload": {"created_by": "advisor_recovery"}},
        attempt_count=0,
        max_attempts=3,
        lease_expires_at=lease_expires_at,
        finished_at=None,
    )


def test_load_recoverable_async_operation_read_models_classifies_supported_operations():
    repository = InMemoryProposalRepository()
    repository.create_operation(
        _operation(
            operation_id="pop_recover_create",
            operation_type="CREATE_PROPOSAL",
            created_at=_now() - timedelta(minutes=2),
        )
    )
    repository.create_operation(
        _operation(
            operation_id="pop_recover_version",
            operation_type="CREATE_PROPOSAL_VERSION",
            created_at=_now() - timedelta(minutes=1),
        )
    )

    read_models = load_recoverable_async_operation_read_models(
        repository=repository,
        as_of=_now(),
    )

    assert [read_model.operation.operation_id for read_model in read_models] == [
        "pop_recover_create",
        "pop_recover_version",
    ]
    assert [read_model.operation_kind for read_model in read_models] == [
        "CREATE_PROPOSAL",
        "CREATE_PROPOSAL_VERSION",
    ]


def test_load_recoverable_async_operation_read_models_preserves_unsupported_operations():
    repository = InMemoryProposalRepository()
    operation = _operation(operation_id="pop_recover_unknown")
    operation.operation_type = "UNKNOWN_OPERATION"
    repository.create_operation(operation)

    read_models = load_recoverable_async_operation_read_models(
        repository=repository,
        as_of=_now(),
    )

    assert len(read_models) == 1
    assert read_models[0].operation.operation_id == "pop_recover_unknown"
    assert read_models[0].operation_kind is None


def test_load_recoverable_async_operation_read_models_uses_repository_recoverability_filter():
    repository = InMemoryProposalRepository()
    repository.create_operation(
        _operation(
            operation_id="pop_recover_expired",
            status="RUNNING",
            lease_expires_at=_now() - timedelta(seconds=1),
        )
    )
    repository.create_operation(
        _operation(
            operation_id="pop_recover_active",
            status="RUNNING",
            lease_expires_at=_now() + timedelta(seconds=30),
        )
    )
    repository.create_operation(
        _operation(
            operation_id="pop_recover_done",
            status="SUCCEEDED",
        )
    )

    read_models = load_recoverable_async_operation_read_models(
        repository=repository,
        as_of=_now(),
    )

    assert [read_model.operation.operation_id for read_model in read_models] == [
        "pop_recover_expired"
    ]
