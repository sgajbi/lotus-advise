from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import ProposalIdPath
from src.api.proposals.memo_parameters import (
    ProposalMemoAiCommentaryIdempotencyKeyHeader,
    ProposalMemoReportPackageIdempotencyKeyHeader,
    ProposalMemoSourceVersionNoPath,
)
from src.api.proposals.memo_responses import (
    MEMO_AI_COMMENTARY_RESPONSES,
    MEMO_REPORT_PACKAGE_RESPONSES,
)
from src.api.proposals.report_errors import run_lotus_report_operation
from src.api.proposals.routes_memo_common import utc_now
from src.core.proposals import (
    ProposalMemoAiCommentaryRequest,
    ProposalMemoAiCommentaryResponse,
    ProposalMemoReportPackageRequest,
    ProposalMemoReportPackageResponse,
)
from src.core.proposals.identifiers import new_memo_event_id, new_report_request_id
from src.core.proposals.memo_api import (
    request_memo_ai_commentary_response,
    request_memo_report_package_response,
)
from src.core.proposals.repository import ProposalRepository


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/report-packages",
    response_model=ProposalMemoReportPackageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Request Proposal Memo Report Package",
    description=(
        "Requests lotus-report materialization for an advisor-reviewed proposal memo package, "
        "submits a typed memo package for deterministic render/archive handling, and records "
        "returned report, render, and archive references in memo lineage. Client-ready document "
        "release remains blocked."
    ),
    responses=MEMO_REPORT_PACKAGE_RESPONSES,
)
def request_proposal_memo_report_package(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    payload: ProposalMemoReportPackageRequest,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
    idempotency_key: ProposalMemoReportPackageIdempotencyKeyHeader = None,
) -> ProposalMemoReportPackageResponse:
    shared._assert_lifecycle_enabled()
    return run_lotus_report_operation(
        lambda: run_proposal_operation(
            lambda: request_memo_report_package_response(
                repository=repository,
                proposal_id=proposal_id,
                version_no=version_no,
                payload=payload,
                idempotency_key=idempotency_key,
                report_request_id=new_report_request_id(),
                event_id=new_memo_event_id(),
                occurred_at=utc_now(),
            )
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/ai-commentary",
    response_model=ProposalMemoAiCommentaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Request Proposal Memo AI Commentary",
    description=(
        "Requests review-gated advisor-use AI commentary for a persisted proposal memo. The "
        "operation requires memo hash continuity and advisor-use review, records only append-only "
        "AI lineage, and cannot alter memo evidence, suitability, approval, or client-ready "
        "publication posture."
    ),
    responses=MEMO_AI_COMMENTARY_RESPONSES,
)
def request_proposal_memo_ai_commentary(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    payload: ProposalMemoAiCommentaryRequest,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
    idempotency_key: ProposalMemoAiCommentaryIdempotencyKeyHeader = None,
) -> ProposalMemoAiCommentaryResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: request_memo_ai_commentary_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=utc_now(),
        )
    )


__all__ = [
    "request_proposal_memo_ai_commentary",
    "request_proposal_memo_report_package",
]
