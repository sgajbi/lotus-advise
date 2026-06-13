from typing import Any, cast

from src.core.proposals import (
    ProposalDetailResponse,
    ProposalExecutionStatusResponse,
    ProposalReportRequest,
    ProposalReportResponse,
    ProposalVersionDetail,
    ProposalWorkflowService,
)
from src.core.proposals.exceptions import ProposalNotFoundError
from src.core.proposals.identifiers import new_report_request_id
from src.core.proposals.report_narrative_package import (
    build_reviewed_narrative_report_package,
    summarize_narrative_report_package,
)
from src.core.replay.models import AdvisoryReplayEvidenceResponse
from src.integrations.lotus_report import request_proposal_report_with_lotus_report

ReportRequestPayload = dict[str, Any]
NarrativeReportPackage = dict[str, Any] | None
NarrativeReportSummary = dict[str, Any] | None


def _related_version_no(
    *,
    proposal: ProposalDetailResponse,
    payload: ProposalReportRequest,
) -> int:
    related_version_no = payload.related_version_no or proposal.proposal.current_version_no
    if related_version_no > proposal.proposal.current_version_no or related_version_no < 1:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return int(related_version_no)


def _reviewed_narrative_report_package(
    *,
    proposal_id: str,
    related_version_no: int,
    payload: ProposalReportRequest,
    service: ProposalWorkflowService,
) -> NarrativeReportPackage:
    if not payload.include_reviewed_narrative:
        return None
    replay = service.get_version_replay(
        proposal_id=proposal_id,
        version_no=related_version_no,
    )
    replay_evidence = _replay_evidence_with_hashes(replay)
    return cast(
        NarrativeReportPackage,
        build_reviewed_narrative_report_package(
            proposal_id=proposal_id,
            version_no=related_version_no,
            replay_evidence=replay_evidence,
        ),
    )


def _replay_evidence_with_hashes(
    replay: AdvisoryReplayEvidenceResponse,
) -> dict[str, Any]:
    replay_evidence = dict(replay.evidence)
    replay_evidence.update(replay.hashes.model_dump(mode="json"))
    return replay_evidence


def _proposal_report_request(
    *,
    request_id: str,
    proposal: ProposalDetailResponse,
    version: ProposalVersionDetail,
    execution_status: ProposalExecutionStatusResponse,
    payload: ProposalReportRequest,
    related_version_no: int,
    narrative_package: NarrativeReportPackage,
) -> ReportRequestPayload:
    return {
        "report_request_id": request_id,
        "proposal": proposal.proposal.model_dump(mode="json"),
        "proposal_version": version.model_dump(mode="json"),
        "report_type": payload.report_type,
        "requested_by": payload.requested_by,
        "related_version_no": related_version_no,
        "include_execution_summary": payload.include_execution_summary,
        "include_reviewed_narrative": payload.include_reviewed_narrative,
        "proposal_narrative_package": narrative_package,
        "execution_status": _execution_status_payload(
            execution_status=execution_status,
            payload=payload,
        ),
    }


def _execution_status_payload(
    *,
    execution_status: ProposalExecutionStatusResponse,
    payload: ProposalReportRequest,
) -> dict[str, Any] | None:
    if not payload.include_execution_summary:
        return None
    return cast(dict[str, Any], execution_status.model_dump(mode="json"))


def _normalize_report_response(
    *,
    response: ProposalReportResponse,
    request_id: str,
    payload: ProposalReportRequest,
    narrative_package: NarrativeReportPackage,
) -> NarrativeReportSummary:
    if response.report_request_id != request_id:
        response.report_request_id = request_id
    narrative_package_summary = cast(
        NarrativeReportSummary,
        summarize_narrative_report_package(narrative_package),
    )
    response.explanation.setdefault(
        "include_reviewed_narrative",
        payload.include_reviewed_narrative,
    )
    if narrative_package_summary is not None:
        response.explanation.setdefault("proposal_narrative_package", narrative_package_summary)
    return narrative_package_summary


def _record_report_request(
    *,
    proposal_id: str,
    response: ProposalReportResponse,
    payload: ProposalReportRequest,
    related_version_no: int,
    narrative_package_summary: NarrativeReportSummary,
    service: ProposalWorkflowService,
) -> None:
    service.record_report_request(
        proposal_id=proposal_id,
        report_response=response,
        requested_by=payload.requested_by,
        related_version_no=related_version_no,
        include_execution_summary=payload.include_execution_summary,
        include_reviewed_narrative=payload.include_reviewed_narrative,
        proposal_narrative_package=narrative_package_summary,
    )


def request_proposal_report(
    *,
    proposal_id: str,
    payload: ProposalReportRequest,
    service: ProposalWorkflowService,
) -> ProposalReportResponse:
    proposal = service.get_proposal(proposal_id=proposal_id, include_evidence=False)
    related_version_no = _related_version_no(proposal=proposal, payload=payload)
    version = service.get_version(
        proposal_id=proposal_id,
        version_no=related_version_no,
        include_evidence=False,
    )

    execution_status = service.get_execution_status(proposal_id=proposal_id)
    narrative_package = _reviewed_narrative_report_package(
        proposal_id=proposal_id,
        related_version_no=related_version_no,
        payload=payload,
        service=service,
    )
    request_id = new_report_request_id()

    request = _proposal_report_request(
        request_id=request_id,
        proposal=proposal,
        version=version,
        execution_status=execution_status,
        payload=payload,
        related_version_no=related_version_no,
        narrative_package=narrative_package,
    )
    response = request_proposal_report_with_lotus_report(request=request)
    narrative_package_summary = _normalize_report_response(
        response=response,
        request_id=request_id,
        payload=payload,
        narrative_package=narrative_package,
    )
    _record_report_request(
        proposal_id=proposal_id,
        response=response,
        payload=payload,
        related_version_no=related_version_no,
        narrative_package_summary=narrative_package_summary,
        service=service,
    )
    return response
