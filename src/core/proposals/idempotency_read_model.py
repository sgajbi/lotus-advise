from dataclasses import dataclass

from src.core.proposals.models import ProposalIdempotencyRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalIdempotencyReadModel:
    record: ProposalIdempotencyRecord | None


def load_proposal_idempotency_read_model(
    *,
    repository: ProposalRepository,
    idempotency_key: str,
) -> ProposalIdempotencyReadModel:
    return ProposalIdempotencyReadModel(
        record=repository.get_idempotency(idempotency_key=idempotency_key),
    )
