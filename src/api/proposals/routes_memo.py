from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends, Header, Path, Query, status

import src.api.proposals.router as shared
from src.api.proposals.errors import raise_proposal_http_exception
from src.core.proposals import (
    ProposalMemoCreateRequest,
    ProposalMemoLineageResponse,
    ProposalMemoProjectionResponse,
    ProposalMemoReplayEvidenceResponse,
    ProposalMemoReportPackageEventRequest,
    ProposalMemoReportPackageEventResponse,
    ProposalMemoResponse,
    ProposalMemoReviewRequest,
    ProposalMemoReviewResponse,
)
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.identifiers import new_memo_event_id
from src.core.proposals.memo_api import (
    create_or_replay_memo_response,
    get_memo_lineage_response,
    get_memo_projection_response,
    get_memo_replay_evidence_response,
    get_memo_response,
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
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal or immutable proposal version was not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused with a different memo-create payload."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": (
                "Memo creation failed validation or finalization is blocked by "
                "source-readiness posture."
            )
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def create_proposal_memo(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    payload: ProposalMemoCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for replay-safe memo creation.",
            examples=["proposal-memo-create-idem-001"],
        ),
    ],
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
) -> ProposalMemoResponse:
    shared._assert_lifecycle_enabled()
    try:
        return create_or_replay_memo_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=_utc_now(),
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo",
    response_model=ProposalMemoResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Read Proposal Memo",
    description=(
        "Returns the exact persisted memo evidence pack, projection policy, append-only memo "
        "audit events, and replay links for an immutable proposal version."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal, immutable proposal version, or persisted memo was not found."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def get_proposal_memo(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
) -> ProposalMemoResponse:
    shared._assert_lifecycle_enabled()
    try:
        return get_memo_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/projection",
    response_model=ProposalMemoProjectionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Read Proposal Memo Projection",
    description=(
        "Returns memo projection policy and audience-filtered sections from the persisted memo. "
        "Projection is read-only and keeps client-ready publication blocked in Slice 7."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal, immutable proposal version, or persisted memo was not found."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def get_proposal_memo_projection(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
    audience: Annotated[
        Optional[str],
        Query(
            description="Optional memo audience filter such as `ADVISOR` or `COMPLIANCE`.",
            examples=["ADVISOR"],
        ),
    ] = None,
) -> ProposalMemoProjectionResponse:
    shared._assert_lifecycle_enabled()
    try:
        return get_memo_projection_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            audience=audience,
        )
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


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
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal, immutable proposal version, or persisted memo was not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": "Idempotency key was reused with a different memo-review payload."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": (
                "Review request is invalid, stale, or attempts unsupported client-ready release."
            )
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def review_proposal_memo(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    payload: ProposalMemoReviewRequest,
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for replay-safe memo review writes.",
            examples=["proposal-memo-review-idem-001"],
        ),
    ] = None,
) -> ProposalMemoReviewResponse:
    shared._assert_lifecycle_enabled()
    try:
        return record_memo_review_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=_utc_now(),
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


@shared.router.post(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/report-package-events",
    response_model=ProposalMemoReportPackageEventResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Record Proposal Memo Report-Package Event",
    description=(
        "Records append-only report-package posture for the persisted memo. Slice 7 records "
        "report-package lineage only; actual report/render/archive realization remains later scope."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal, immutable proposal version, or persisted memo was not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": (
                "Idempotency key was reused with a different report-package event payload."
            )
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Report-package event is invalid or references a stale memo hash."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def record_proposal_memo_report_package_event(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    payload: ProposalMemoReportPackageEventRequest,
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for replay-safe memo report-package events.",
            examples=["proposal-memo-report-package-idem-001"],
        ),
    ] = None,
) -> ProposalMemoReportPackageEventResponse:
    shared._assert_lifecycle_enabled()
    try:
        return record_memo_report_package_event_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
            payload=payload,
            idempotency_key=idempotency_key,
            event_id=new_memo_event_id(),
            occurred_at=_utc_now(),
        )
    except (
        ProposalIdempotencyConflictError,
        ProposalNotFoundError,
        ProposalValidationError,
    ) as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/memos/lineage",
    response_model=ProposalMemoLineageResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Get Proposal Memo Lineage",
    description=(
        "Returns persisted memo lineage for a proposal, including memo hashes, source hashes, "
        "lifecycle status, and event counts."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Proposal was not found."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def get_proposal_memo_lineage(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
) -> ProposalMemoLineageResponse:
    shared._assert_lifecycle_enabled()
    try:
        return get_memo_lineage_response(repository=repository, proposal_id=proposal_id)
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


@shared.router.get(
    "/advisory/proposals/{proposal_id}/versions/{version_no}/memo/replay-evidence",
    response_model=ProposalMemoReplayEvidenceResponse,
    status_code=status.HTTP_200_OK,
    tags=["Advisory Proposal Memo"],
    summary="Get Proposal Memo Replay Evidence",
    description=(
        "Returns memo replay evidence with proposal source hashes, memo hashes, replay metadata, "
        "projection posture, and append-only memo audit events."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Proposal, immutable proposal version, or persisted memo was not found."
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Proposal runtime persistence is unavailable or misconfigured."
        },
    },
)
def get_proposal_memo_replay_evidence(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number used as memo source.", ge=1),
    ],
    repository: Annotated[
        ProposalRepository,
        Depends(shared.get_proposal_repository),
    ],
) -> ProposalMemoReplayEvidenceResponse:
    shared._assert_lifecycle_enabled()
    try:
        return get_memo_replay_evidence_response(
            repository=repository,
            proposal_id=proposal_id,
            version_no=version_no,
        )
    except ProposalNotFoundError as exc:
        raise_proposal_http_exception(exc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
