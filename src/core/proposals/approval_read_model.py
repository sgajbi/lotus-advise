from dataclasses import dataclass

from src.core.proposals.models import ProposalApprovalRecordData, ProposalRecord
from src.core.proposals.repository import ProposalRepository


@dataclass(frozen=True)
class ProposalApprovalReadModel:
    proposal: ProposalRecord | None
    approvals: list[ProposalApprovalRecordData]


def load_proposal_approval_read_model(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalApprovalReadModel:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        return ProposalApprovalReadModel(proposal=None, approvals=[])

    return ProposalApprovalReadModel(
        proposal=proposal,
        approvals=repository.list_approvals(proposal_id=proposal_id),
    )
