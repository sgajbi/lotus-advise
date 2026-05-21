from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalRecord,
    ProposalTransitionResult,
    ProposalWorkflowEventRecord,
)
from src.core.proposals.repository import ProposalRepository


def persist_proposal_transition(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
) -> ProposalTransitionResult:
    return repository.transition_proposal(proposal=proposal, event=event, approval=None)


def persist_proposal_approval_transition(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
    approval: ProposalApprovalRecordData,
) -> ProposalTransitionResult:
    return repository.transition_proposal(proposal=proposal, event=event, approval=approval)
