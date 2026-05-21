from datetime import datetime, timezone

from src.core.proposals.idempotency_read_model import load_proposal_idempotency_read_model
from src.core.proposals.models import ProposalIdempotencyRecord
from src.infrastructure.proposals.in_memory import InMemoryProposalRepository


def _record() -> ProposalIdempotencyRecord:
    return ProposalIdempotencyRecord(
        idempotency_key="idem_read_model",
        request_hash="sha256:req-read-model",
        proposal_id="pp_read_model",
        proposal_version_no=2,
        created_at=datetime(2026, 5, 21, 16, 0, tzinfo=timezone.utc),
    )


def test_load_proposal_idempotency_read_model_returns_replay_record():
    repository = InMemoryProposalRepository()
    repository.save_idempotency(_record())

    read_model = load_proposal_idempotency_read_model(
        repository=repository,
        idempotency_key="idem_read_model",
    )

    assert read_model.record is not None
    assert read_model.record.proposal_id == "pp_read_model"
    assert read_model.record.proposal_version_no == 2


def test_load_proposal_idempotency_read_model_preserves_missing_key_boundary():
    read_model = load_proposal_idempotency_read_model(
        repository=InMemoryProposalRepository(),
        idempotency_key="idem_missing",
    )

    assert read_model.record is None
