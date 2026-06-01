from __future__ import annotations

from src.core.proposals.activity_read_model import load_proposal_activity_read_model
from src.core.proposals.delivery_summary import (
    build_delivery_history_response,
    build_delivery_summary_response,
)
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.execution_status import build_execution_status_response
from src.core.proposals.models import (
    ProposalDeliveryHistoryResponse,
    ProposalDeliverySummaryResponse,
    ProposalExecutionStatusResponse,
    ProposalWorkflowTimelineResponse,
)
from src.core.proposals.projections import build_workflow_timeline_response
from src.core.proposals.repository import ProposalRepository


def build_workflow_timeline_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalWorkflowTimelineResponse:
    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if activity.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    return build_workflow_timeline_response(proposal=activity.proposal, events=activity.events)


def build_execution_status_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalExecutionStatusResponse:
    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if activity.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    return build_execution_status_response(proposal=activity.proposal, events=activity.events)


def build_delivery_summary_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalDeliverySummaryResponse:
    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if activity.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    return build_delivery_summary_response(proposal=activity.proposal, events=activity.events)


def build_delivery_history_view(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalDeliveryHistoryResponse:
    activity = load_proposal_activity_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if activity.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    return build_delivery_history_response(proposal=activity.proposal, events=activity.events)


__all__ = [
    "build_delivery_history_view",
    "build_delivery_summary_view",
    "build_execution_status_view",
    "build_workflow_timeline_view",
]
