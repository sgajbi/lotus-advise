import uuid

from src.core.proposals import (
    ProposalNotFoundError,
    ProposalReportRequest,
    ProposalReportResponse,
    ProposalWorkflowService,
)
from src.integrations.lotus_report import request_proposal_report_with_lotus_report


def request_proposal_report(
    *,
    proposal_id: str,
    payload: ProposalReportRequest,
    service: ProposalWorkflowService,
) -> ProposalReportResponse:
    proposal = service.get_proposal(proposal_id=proposal_id, include_evidence=False)
    related_version_no = payload.related_version_no or proposal.proposal.current_version_no
    if related_version_no > proposal.proposal.current_version_no or related_version_no < 1:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    version = service.get_version(
        proposal_id=proposal_id,
        version_no=related_version_no,
        include_evidence=False,
    )

    execution_status = service.get_execution_status(proposal_id=proposal_id)
    request_id = f"prr_{uuid.uuid4().hex[:12]}"

    request = {
        "report_request_id": request_id,
        "proposal": proposal.proposal.model_dump(mode="json"),
        "proposal_version": version.model_dump(mode="json"),
        "report_type": payload.report_type,
        "requested_by": payload.requested_by,
        "related_version_no": related_version_no,
        "include_execution_summary": payload.include_execution_summary,
        "execution_status": (
            execution_status.model_dump(mode="json") if payload.include_execution_summary else None
        ),
    }
    response = request_proposal_report_with_lotus_report(request=request)
    if response.report_request_id != request_id:
        response.report_request_id = request_id
    return response
