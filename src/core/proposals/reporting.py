from datetime import datetime

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
) -> ProposalWorkflowEventRecord:
    occurred_at = datetime.fromisoformat(report_response.generated_at)
    return ProposalWorkflowEventRecord(
        event_id=event_id,
        proposal_id=proposal.proposal_id,
        event_type="REPORT_REQUESTED",
        from_state=proposal.current_state,
        to_state=proposal.current_state,
        actor_id=requested_by,
        occurred_at=occurred_at,
        reason_json={
            "report_request_id": report_response.report_request_id,
            "report_type": report_response.report_type,
            "report_service": report_response.report_service,
            "status": report_response.status,
            "report_reference_id": report_response.report_reference_id,
            "artifact_url": report_response.artifact_url,
            "related_version_no": related_version_no,
            "include_execution_summary": include_execution_summary,
        },
        related_version_no=related_version_no,
    )


def apply_report_request_state(
    *,
    proposal: ProposalRecord,
    event: ProposalWorkflowEventRecord,
) -> None:
    proposal.last_event_at = max(proposal.last_event_at, event.occurred_at)
