from typing import Any

from src.core.proposals.command_read_model import load_proposal_command_read_model
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.models import ProposalReportResponse, ProposalWorkflowEventRecord
from src.core.proposals.reporting import build_report_request_event_and_apply_state
from src.core.proposals.repository import ProposalRepository
from src.core.proposals.transition_persistence import persist_proposal_transition


def record_proposal_report_request(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    report_response: ProposalReportResponse,
    requested_by: str,
    related_version_no: int,
    include_execution_summary: bool,
    include_reviewed_narrative: bool = False,
    proposal_narrative_package: dict[str, Any] | None = None,
    event_id: str,
) -> ProposalWorkflowEventRecord:
    command_read_model = load_proposal_command_read_model(
        repository=repository,
        proposal_id=proposal_id,
    )
    if command_read_model.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    proposal = command_read_model.proposal

    event = build_report_request_event_and_apply_state(
        event_id=event_id,
        proposal=proposal,
        report_response=report_response,
        requested_by=requested_by,
        related_version_no=related_version_no,
        include_execution_summary=include_execution_summary,
        include_reviewed_narrative=include_reviewed_narrative,
        proposal_narrative_package=proposal_narrative_package,
    )
    persist_proposal_transition(
        repository=repository,
        proposal=proposal,
        event=event,
    )
    return event
