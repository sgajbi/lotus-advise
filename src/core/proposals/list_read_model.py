from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.proposals.models import ProposalRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalListReadModel:
    proposals: list[ProposalRecord]
    next_cursor: str | None


def load_proposal_list_read_model(
    *,
    repository: ProposalRepository,
    portfolio_id: Optional[str],
    state: Optional[str],
    created_by: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
    limit: int,
    cursor: Optional[str],
) -> ProposalListReadModel:
    proposals, next_cursor = repository.list_proposals(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )
    return ProposalListReadModel(proposals=proposals, next_cursor=next_cursor)
