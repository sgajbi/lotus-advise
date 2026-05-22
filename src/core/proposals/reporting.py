from datetime import datetime
from typing import Any

from src.core.proposals.models import (
    ProposalRecord,
    ProposalReportResponse,
    ProposalWorkflowEventRecord,
)


def build_report_requested_event(
    *,
    event_id: str,
    proposal: ProposalRecord,
    report_response: ProposalReportResponse,
    requested_by: str,
    related_version_no: int,
    include_execution_summary: bool,
    include_reviewed_narrative: bool = False,
    proposal_narrative_package: dict[str, Any] | None = None,
) -> ProposalWorkflowEventRecord:
    occurred_at = datetime.fromisoformat(report_response.generated_at)
    reason_json: dict[str, Any] = {
        "report_request_id": report_response.report_request_id,
        "report_type": report_response.report_type,
        "report_service": report_response.report_service,
        "status": report_response.status,
        "report_reference_id": report_response.report_reference_id,
        "artifact_url": report_response.artifact_url,
        "related_version_no": related_version_no,
        "include_execution_summary": include_execution_summary,
    }
    if include_reviewed_narrative:
        reason_json["include_reviewed_narrative"] = True
    if proposal_narrative_package is not None:
        reason_json["proposal_narrative_package"] = proposal_narrative_package
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type="REPORT_REQUESTED",
        from_state=proposal.current_state,
        to_state=proposal.current_state,
        actor_id=requested_by,
        occurred_at=occurred_at,
        reason_json=reason_json,
        related_version_no=related_version_no,
    )


def apply_report_request_state(
    *,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
) -> None:
    proposal.last_event_at = max(proposal.last_event_at, event.occurred_at)


def build_report_request_event_and_apply_state(
    *,
    event_id: str,
    proposal: ProposalRecord,
    report_response: ProposalReportResponse,
    requested_by: str,
    related_version_no: int,
    include_execution_summary: bool,
    include_reviewed_narrative: bool = False,
    proposal_narrative_package: dict[str, Any] | None = None,
) -> ProposalWorkflowEventRecord:
    event = build_report_requested_event(
        event_id=event_id,
        proposal=proposal,
        report_response=report_response,
        requested_by=requested_by,
        related_version_no=related_version_no,
        include_execution_summary=include_execution_summary,
        include_reviewed_narrative=include_reviewed_narrative,
        proposal_narrative_package=proposal_narrative_package,
    )
    apply_report_request_state(proposal=proposal, event=event)
    return event
