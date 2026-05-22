from src.api.services.proposal_report_narrative import (
    build_reviewed_narrative_report_package,
    summarize_narrative_report_package,
)
from src.core.proposals import (
    ProposalReportRequest,
    ProposalReportResponse,
    ProposalWorkflowService,
)
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.identifiers import new_report_request_id
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
    narrative_package = None
    if payload.include_reviewed_narrative:
        replay = service.get_version_replay(
            proposal_id=proposal_id,
            version_no=related_version_no,
        )
        replay_evidence = dict(replay.evidence)
        replay_evidence.update(replay.hashes.model_dump(mode="json"))
        narrative_package = build_reviewed_narrative_report_package(
            proposal_id=proposal_id,
            version_no=related_version_no,
            replay_evidence=replay_evidence,
        )
    request_id = new_report_request_id()

    request = {
        "report_request_id": request_id,
        "proposal": proposal.proposal.model_dump(mode="json"),
        "proposal_version": version.model_dump(mode="json"),
        "report_type": payload.report_type,
        "requested_by": payload.requested_by,
        "related_version_no": related_version_no,
        "include_execution_summary": payload.include_execution_summary,
        "include_reviewed_narrative": payload.include_reviewed_narrative,
        "proposal_narrative_package": narrative_package,
        "execution_status": (
            execution_status.model_dump(mode="json") if payload.include_execution_summary else None
        ),
    }
    response = request_proposal_report_with_lotus_report(request=request)
    if response.report_request_id != request_id:
        response.report_request_id = request_id
    narrative_package_summary = summarize_narrative_report_package(narrative_package)
    response.explanation.setdefault(
        "include_reviewed_narrative",
        payload.include_reviewed_narrative,
    )
    if narrative_package_summary is not None:
        response.explanation.setdefault("proposal_narrative_package", narrative_package_summary)
    service.record_report_request(
        proposal_id=proposal_id,
        report_response=response,
        requested_by=payload.requested_by,
        related_version_no=related_version_no,
        include_execution_summary=payload.include_execution_summary,
        include_reviewed_narrative=payload.include_reviewed_narrative,
        proposal_narrative_package=narrative_package_summary,
    )
    return response
