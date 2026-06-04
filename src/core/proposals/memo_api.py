from __future__ import annotations

from datetime import datetime

from src.core.common.idempotency import normalize_optional_idempotency_key
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.idempotency_validation import require_proposal_idempotency_key
from src.core.proposals.memo_event_recording import (
    append_or_replay_memo_event,
    memo_event_request_hash,
)
from src.core.proposals.memo_external_request_operations import (
    request_memo_ai_commentary_operation,
    request_memo_report_package_operation,
)
from src.core.proposals.memo_persistence import (
    ProposalMemoPersistenceError,
    create_or_replay_proposal_memo,
)
from src.core.proposals.memo_request_context import (
    load_memo_for_proposal_version,
    load_proposal_version_for_memo,
    validate_source_memo_hash,
)
from src.core.proposals.memo_response_projection import (
    build_memo_lineage_response,
    build_memo_projection_response,
    build_memo_replay_evidence_response,
    build_memo_response,
)
from src.core.proposals.memo_response_projection import (
    to_audit_event as _to_audit_event,
)
from src.core.proposals.models import (
    ProposalMemoAiCommentaryRequest,
    ProposalMemoAiCommentaryResponse,
    ProposalMemoCreateRequest,
    ProposalMemoLineageResponse,
    ProposalMemoProjectionResponse,
    ProposalMemoReplayEvidenceResponse,
    ProposalMemoReportPackageEventRequest,
    ProposalMemoReportPackageEventResponse,
    ProposalMemoReportPackageRequest,
    ProposalMemoReportPackageResponse,
    ProposalMemoResponse,
    ProposalMemoReviewRequest,
    ProposalMemoReviewResponse,
)
from src.core.proposals.repository import ProposalRepository
from src.integrations.lotus_ai import (
    LotusAIProposalMemoUnavailableError,
    build_proposal_memo_ai_unavailable_commentary,
    generate_proposal_memo_commentary_with_lotus_ai,
)
from src.integrations.lotus_report import request_proposal_memo_report_package_with_lotus_report


def create_or_replay_memo_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalMemoCreateRequest,
    idempotency_key: str,
    event_id: str,
    occurred_at: datetime,
) -> ProposalMemoResponse:
    idempotency_key = require_proposal_idempotency_key(idempotency_key)
    proposal, version = load_proposal_version_for_memo(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    try:
        result = create_or_replay_proposal_memo(
            repository=repository,
            version=version,
            idempotency_key=idempotency_key,
            created_by=payload.created_by,
            created_at=occurred_at,
            event_id=event_id,
            lifecycle_status=payload.lifecycle_status,
            reason=payload.reason,
        )
    except ProposalMemoPersistenceError as exc:
        _raise_api_error(exc)
    return build_memo_response(
        repository=repository,
        proposal=proposal,
        memo=result.memo,
    )


def get_memo_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalMemoResponse:
    proposal, _version = load_proposal_version_for_memo(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = load_memo_for_proposal_version(
        repository=repository, proposal_id=proposal_id, version_no=version_no
    )
    return build_memo_response(repository=repository, proposal=proposal, memo=memo)


def get_memo_projection_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    audience: str | None,
) -> ProposalMemoProjectionResponse:
    memo_response = get_memo_response(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    return build_memo_projection_response(memo_response=memo_response, audience=audience)


def record_memo_review_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalMemoReviewRequest,
    idempotency_key: str | None,
    event_id: str,
    occurred_at: datetime,
) -> ProposalMemoReviewResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    proposal, _version = load_proposal_version_for_memo(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = load_memo_for_proposal_version(
        repository=repository, proposal_id=proposal_id, version_no=version_no
    )
    validate_source_memo_hash(memo=memo, source_memo_hash=payload.source_memo_hash)
    if payload.client_ready_release_requested:
        raise ProposalValidationError("MEMO_CLIENT_READY_RELEASE_NOT_SUPPORTED")
    request_hash = memo_event_request_hash(
        {
            "operation": "MEMO_REVIEW_RECORDED",
            "memo_id": memo.memo_id,
            "action": payload.action,
            "reviewed_by": payload.reviewed_by,
            "reason": payload.reason,
            "source_memo_hash": payload.source_memo_hash,
            "client_ready_release_requested": payload.client_ready_release_requested,
        }
    )
    event, replayed = append_or_replay_memo_event(
        repository=repository,
        memo=memo,
        event_id=event_id,
        event_type="MEMO_REVIEW_RECORDED",
        actor_id=payload.reviewed_by,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        reason={
            "review_action": payload.action,
            "review_reason": payload.reason,
            "source_memo_hash": payload.source_memo_hash,
            "client_ready_release_requested": payload.client_ready_release_requested,
            "client_ready_publication": "BLOCKED",
        },
    )
    return ProposalMemoReviewResponse(
        memo=build_memo_response(repository=repository, proposal=proposal, memo=memo),
        review_event=_to_audit_event(event),
        replayed=replayed,
    )


def record_memo_report_package_event_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalMemoReportPackageEventRequest,
    idempotency_key: str | None,
    event_id: str,
    occurred_at: datetime,
) -> ProposalMemoReportPackageEventResponse:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    proposal, _version = load_proposal_version_for_memo(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = load_memo_for_proposal_version(
        repository=repository, proposal_id=proposal_id, version_no=version_no
    )
    validate_source_memo_hash(memo=memo, source_memo_hash=payload.source_memo_hash)
    request_hash = memo_event_request_hash(
        {
            "operation": "MEMO_REPORT_PACKAGE_RECORDED",
            "memo_id": memo.memo_id,
            "recorded_by": payload.recorded_by,
            "report_package_id": payload.report_package_id,
            "report_package_status": payload.report_package_status,
            "source_memo_hash": payload.source_memo_hash,
            "reason": payload.reason,
        }
    )
    event, replayed = append_or_replay_memo_event(
        repository=repository,
        memo=memo,
        event_id=event_id,
        event_type="MEMO_REPORT_PACKAGE_RECORDED",
        actor_id=payload.recorded_by,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        reason={
            "report_package_id": payload.report_package_id,
            "report_package_status": payload.report_package_status,
            "source_memo_hash": payload.source_memo_hash,
            "client_ready_publication": "BLOCKED",
            "reason": payload.reason,
        },
    )
    return ProposalMemoReportPackageEventResponse(
        memo=build_memo_response(repository=repository, proposal=proposal, memo=memo),
        report_package_event=_to_audit_event(event),
        replayed=replayed,
    )


def request_memo_report_package_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalMemoReportPackageRequest,
    idempotency_key: str | None,
    report_request_id: str,
    event_id: str,
    occurred_at: datetime,
) -> ProposalMemoReportPackageResponse:
    return request_memo_report_package_operation(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
        payload=payload,
        idempotency_key=idempotency_key,
        report_request_id=report_request_id,
        event_id=event_id,
        occurred_at=occurred_at,
        request_report_package=request_proposal_memo_report_package_with_lotus_report,
    )


def request_memo_ai_commentary_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
    payload: ProposalMemoAiCommentaryRequest,
    idempotency_key: str | None,
    event_id: str,
    occurred_at: datetime,
) -> ProposalMemoAiCommentaryResponse:
    return request_memo_ai_commentary_operation(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
        payload=payload,
        idempotency_key=idempotency_key,
        event_id=event_id,
        occurred_at=occurred_at,
        generate_commentary=generate_proposal_memo_commentary_with_lotus_ai,
        build_unavailable_commentary=build_proposal_memo_ai_unavailable_commentary,
        unavailable_error=LotusAIProposalMemoUnavailableError,
    )


def get_memo_lineage_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalMemoLineageResponse:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    memos = repository.list_memos(proposal_id=proposal_id)
    return build_memo_lineage_response(
        repository=repository,
        proposal=proposal,
        memos=memos,
    )


def get_memo_replay_evidence_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalMemoReplayEvidenceResponse:
    memo_response = get_memo_response(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    return build_memo_replay_evidence_response(
        proposal_id=proposal_id,
        version_no=version_no,
        memo_response=memo_response,
    )


def _raise_api_error(exc: ProposalMemoPersistenceError) -> None:
    message = str(exc)
    if "IDEMPOTENCY" in message and "CONFLICT" in message:
        raise ProposalIdempotencyConflictError(message) from exc
    raise ProposalValidationError(message) from exc
