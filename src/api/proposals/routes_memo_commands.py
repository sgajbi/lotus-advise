from fastapi import Depends, status

import src.api.proposals.router as shared
from src.api.proposals.errors import run_proposal_operation
from src.api.proposals.lifecycle_parameters import ProposalIdPath
from src.api.proposals.memo_parameters import (
    ProposalMemoCreateIdempotencyKeyHeader,
    ProposalMemoReportPackageEventIdempotencyKeyHeader,
    ProposalMemoReviewIdempotencyKeyHeader,
    ProposalMemoSourceVersionNoPath,
)
from src.api.proposals.memo_responses import (
    MEMO_CREATE_RESPONSES,
    MEMO_REPORT_PACKAGE_EVENT_RESPONSES,
    MEMO_REVIEW_RESPONSES,
)
from src.api.proposals.routes_memo_common import utc_now
from src.core.proposals import (
    ProposalMemoCreateRequest,
    ProposalMemoReportPackageEventRequest,
    ProposalMemoReportPackageEventResponse,
    ProposalMemoResponse,
    ProposalMemoReviewRequest,
    ProposalMemoReviewResponse,
)
from src.core.proposals.identifiers import new_memo_event_id
from src.core.proposals.memo_api import (
    create_or_replay_memo_response,
    record_memo_report_package_event_response,
    record_memo_review_response,
)
from src.core.proposals.repository import ProposalRepository


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo",
    response_model=ProposalMemoResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Create Or Replay Proposal Memo",
    description=(
        "Creates or replays a persisted RFC-0024 advisor proposal memo evidence pack from an "
        "immutable proposal version. The route is idempotent, hash-backed, and does not publish "
        "client-ready memo content."
    ),
    responses=MEMO_CREATE_RESPONSES,
)
def create_proposal_memo(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    payload: ProposalMemoCreateRequest,
    idempotency_key: ProposalMemoCreateIdempotencyKeyHeader,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
) -> ProposalMemoResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: create_or_replay_memo_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=utc_now(),
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/review",
    response_model=ProposalMemoReviewResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Record Proposal Memo Review",
    description=(
        "Records an idempotent review event against the persisted memo hash. The operation is "
        "append-only, rejects stale memo hashes, and cannot release client-ready publication."
    ),
    responses=MEMO_REVIEW_RESPONSES,
)
def review_proposal_memo(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    payload: ProposalMemoReviewRequest,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
    idempotency_key: ProposalMemoReviewIdempotencyKeyHeader = None,
) -> ProposalMemoReviewResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: record_memo_review_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=utc_now(),
        )
    )


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/report-package-events",
    response_model=ProposalMemoReportPackageEventResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Record Proposal Memo Report-Package Event",
    description=(
        "Records append-only report-package posture for the persisted memo, including report, "
        "render, and archive status received from the reporting owner. This endpoint records "
        "external lineage; use the report-package request endpoint when Advise must request "
        "Lotus Report materialization. Client-ready document release remains blocked."
    ),
    responses=MEMO_REPORT_PACKAGE_EVENT_RESPONSES,
)
def record_proposal_memo_report_package_event(
    proposal_id: ProposalIdPath,
    version_no: ProposalMemoSourceVersionNoPath,
    payload: ProposalMemoReportPackageEventRequest,
    repository: ProposalRepository = Depends(shared.get_proposal_repository),
    idempotency_key: ProposalMemoReportPackageEventIdempotencyKeyHeader = None,
) -> ProposalMemoReportPackageEventResponse:
    shared._assert_lifecycle_enabled()
    return run_proposal_operation(
        lambda: record_memo_report_package_event_response(
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
    "create_proposal_memo",
    "record_proposal_memo_report_package_event",
    "review_proposal_memo",
]
