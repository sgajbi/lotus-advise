from datetime import datetime, timezone

from src.core.proposals.async_operation_read_model import (
    load_proposal_async_operation_by_correlation_read_model,
    load_proposal_async_operation_read_model,
)
from src.core.proposals.models import ProposalAsyncOperationRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _operation() -> ProposalAsyncOperationRecord:
    return ProposalAsyncOperationRecord(
        operation_id="pop_read_model",
        operation_type="CREATE_PROPOSAL",
        status="PENDING",
        correlation_id="corr_read_model",
        idempotency_key="idem_read_model",
        proposal_id=None,
        created_by="advisor_async_read_model",
        created_at=datetime(2026, 5, 21, 17, 0, tzinfo=timezone.utc),
        payload_json={"created_by": "advisor_async_read_model"},
        attempt_count=0,
        max_attempts=3,
    )


def test_load_proposal_async_operation_read_model_returns_operation_by_id():
    repository = InMemoryProposalRepository()
    repository.create_operation(_operation())

    read_model = load_proposal_async_operation_read_model(
        repository=repository,
        operation_id="pop_read_model",
    )

    assert read_model.operation is not None
    assert read_model.operation.correlation_id == "corr_read_model"
    assert read_model.operation.idempotency_key == "idem_read_model"


def test_load_proposal_async_operation_read_model_preserves_missing_operation_boundary():
    read_model = load_proposal_async_operation_read_model(
        repository=InMemoryProposalRepository(),
        operation_id="pop_missing",
    )

    assert read_model.operation is None


def test_load_proposal_async_operation_by_correlation_read_model_returns_operation():
    repository = InMemoryProposalRepository()
    repository.create_operation(_operation())

    read_model = load_proposal_async_operation_by_correlation_read_model(
        repository=repository,
        correlation_id="corr_read_model",
    )

    assert read_model.operation is not None
    assert read_model.operation.operation_id == "pop_read_model"


def test_load_proposal_async_operation_by_correlation_read_model_preserves_missing_boundary():
    read_model = load_proposal_async_operation_by_correlation_read_model(
        repository=InMemoryProposalRepository(),
        correlation_id="corr_missing",
    )

    assert read_model.operation is None
