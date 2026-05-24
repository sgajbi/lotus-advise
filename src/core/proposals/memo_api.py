from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import (
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalValidationError,
)
from src.core.proposals.memo_persistence import (
    ProposalMemoPersistenceError,
    create_or_replay_proposal_memo,
)
from src.core.proposals.models import (
    ProposalMemoAuditEvent,
    ProposalMemoCreateRequest,
    ProposalMemoLineageItem,
    ProposalMemoLineageResponse,
    ProposalMemoProjectionResponse,
    ProposalMemoReplayEvidenceResponse,
    ProposalMemoReportPackageEventRequest,
    ProposalMemoReportPackageEventResponse,
    ProposalMemoResponse,
    ProposalMemoReviewRequest,
    ProposalMemoReviewResponse,
    ProposalRecord,
    ProposalVersionRecord,
)
from src.core.proposals.persistence_models import (
    ProposalMemoEventRecord,
    ProposalMemoEventType,
    ProposalMemoRecord,
)
from src.core.proposals.projections import to_proposal_summary
from src.core.proposals.proposal_replay import load_proposal_version_replay_referents
from src.core.proposals.repository import ProposalRepository


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
    proposal, version = _load_proposal_version(
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
    proposal, _version = _load_proposal_version(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = _load_memo(repository=repository, proposal_id=proposal_id, version_no=version_no)
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
    sections = _project_sections(memo_response.memo, audience=audience)
    return ProposalMemoProjectionResponse(
        proposal=memo_response.proposal,
        proposal_version_no=memo_response.proposal_version_no,
        memo_id=memo_response.memo_id,
        memo_hash=memo_response.memo_hash,
        audience=audience,
        projection=memo_response.projection,
        sections=sections,
        projection_posture={
            "source": "PERSISTED_MEMO_RECORD",
            "mutation_performed": False,
            "audience_filter": audience,
            "client_ready_publication": memo_response.projection.get(
                "client_ready_publication", "BLOCKED"
            ),
            "gateway_supported": False,
            "workbench_supported": False,
        },
    )


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
    proposal, _version = _load_proposal_version(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = _load_memo(repository=repository, proposal_id=proposal_id, version_no=version_no)
    _validate_source_memo_hash(memo=memo, source_memo_hash=payload.source_memo_hash)
    if payload.client_ready_release_requested:
        raise ProposalValidationError("MEMO_CLIENT_READY_RELEASE_NOT_SUPPORTED")
    request_hash = _request_hash(
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
    event, replayed = _append_or_replay_memo_event(
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
    proposal, _version = _load_proposal_version(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    memo = _load_memo(repository=repository, proposal_id=proposal_id, version_no=version_no)
    _validate_source_memo_hash(memo=memo, source_memo_hash=payload.source_memo_hash)
    request_hash = _request_hash(
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
    event, replayed = _append_or_replay_memo_event(
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


def get_memo_lineage_response(
    *,
    repository: ProposalRepository,
    proposal_id: str,
) -> ProposalMemoLineageResponse:
    proposal = repository.get_proposal(proposal_id=proposal_id)
    if proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    memos = repository.list_memos(proposal_id=proposal_id)
    items = [
        ProposalMemoLineageItem(
            memo_id=memo.memo_id,
            proposal_version_no=memo.proposal_version_no,
            proposal_version_id=memo.proposal_version_id,
            memo_status=memo.memo_status,
            lifecycle_status=memo.lifecycle_status,
            memo_hash=memo.memo_hash,
            source_input_hash=memo.source_input_hash,
            created_at=memo.created_at.isoformat(),
            event_count=len(repository.list_memo_events(memo_id=memo.memo_id)),
        )
        for memo in memos
    ]
    return ProposalMemoLineageResponse(
        proposal=to_proposal_summary(proposal),
        memo_count=len(items),
        latest_memo_id=items[-1].memo_id if items else None,
        lineage_complete=all(_memo_has_replay_metadata(memo) for memo in memos),
        memos=items,
        lineage_posture={
            "source": "PERSISTED_MEMO_RECORDS",
            "memo_api_supported": True,
            "gateway_supported": False,
            "workbench_supported": False,
            "client_ready_publication": "BLOCKED",
        },
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
    replay_metadata = memo_response.replay_metadata
    return ProposalMemoReplayEvidenceResponse(
        subject={
            "proposal_id": proposal_id,
            "proposal_version_no": version_no,
            "proposal_version_id": memo_response.proposal_version_id,
            "memo_id": memo_response.memo_id,
        },
        hashes={
            "memo_hash": memo_response.memo_hash,
            "source_input_hash": memo_response.source_input_hash,
            "proposal_request_hash": replay_metadata.get("proposal_request_hash"),
            "proposal_artifact_hash": replay_metadata.get("proposal_artifact_hash"),
            "proposal_simulation_hash": replay_metadata.get("proposal_simulation_hash"),
            "memo_request_hash": replay_metadata.get("memo_request_hash"),
        },
        replay_metadata=replay_metadata,
        audit_events=memo_response.audit_events,
        evidence={
            "memo_status": memo_response.memo_status,
            "lifecycle_status": memo_response.lifecycle_status,
            "projection": memo_response.projection,
            "review_posture": memo_response.review_posture,
            "report_package_posture": memo_response.report_package_posture,
        },
        explanation={
            "source": "PERSISTED_MEMO_RECORD",
            "replay_policy": replay_metadata.get("replay_policy", "EXACT_SOURCE_HASH_MATCH"),
            "mutation_performed": False,
            "client_ready_publication": "BLOCKED",
            "gateway_supported": False,
            "workbench_supported": False,
        },
    )


def build_memo_response(
    *,
    repository: ProposalRepository,
    proposal: ProposalRecord,
    memo: ProposalMemoRecord,
) -> ProposalMemoResponse:
    events = repository.list_memo_events(memo_id=memo.memo_id)
    projection = dict(memo.projection_json)
    projection.setdefault("client_ready_publication", "BLOCKED")
    return ProposalMemoResponse(
        proposal=to_proposal_summary(proposal),
        proposal_version_no=memo.proposal_version_no,
        proposal_version_id=memo.proposal_version_id,
        memo_id=memo.memo_id,
        artifact_id=memo.artifact_id,
        memo_version=memo.memo_version,
        memo_status=memo.memo_status,
        lifecycle_status=memo.lifecycle_status,
        created_by=memo.created_by,
        created_at=memo.created_at.isoformat(),
        source_input_hash=memo.source_input_hash,
        memo_hash=memo.memo_hash,
        memo=dict(memo.memo_json),
        projection=projection,
        review_posture=_latest_event_posture(events, event_type="MEMO_REVIEW_RECORDED"),
        report_package_posture=_latest_event_posture(
            events, event_type="MEMO_REPORT_PACKAGE_RECORDED"
        ),
        replay_metadata=dict(memo.replay_metadata_json),
        audit_events=[_to_audit_event(event) for event in events],
        event_count=len(events),
        replay_evidence_path=(
            f"/advisory/proposals/{memo.proposal_id}/versions/"
            f"{memo.proposal_version_no}/memo/replay-evidence"
        ),
        lineage_path=f"/advisory/proposals/{memo.proposal_id}/memos/lineage",
        read_posture={
            "source": "PERSISTED_MEMO_RECORD",
            "memo_api_supported": True,
            "report_package_generation_supported": False,
            "gateway_supported": False,
            "workbench_supported": False,
            "client_ready_publication": projection["client_ready_publication"],
        },
    )


def _load_proposal_version(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> tuple[ProposalRecord, ProposalVersionRecord]:
    referents = load_proposal_version_replay_referents(
        repository=repository,
        proposal_id=proposal_id,
        version_no=version_no,
    )
    if referents.proposal is None:
        raise ProposalNotFoundError("PROPOSAL_NOT_FOUND")
    if referents.version is None:
        raise ProposalNotFoundError("PROPOSAL_VERSION_NOT_FOUND")
    return referents.proposal, referents.version


def _load_memo(
    *,
    repository: ProposalRepository,
    proposal_id: str,
    version_no: int,
) -> ProposalMemoRecord:
    memo = repository.get_memo_by_proposal_version(
        proposal_id=proposal_id,
        proposal_version_no=version_no,
    )
    if memo is None:
        raise ProposalNotFoundError("PROPOSAL_MEMO_NOT_FOUND")
    return memo


def _append_or_replay_memo_event(
    *,
    repository: ProposalRepository,
    memo: ProposalMemoRecord,
    event_id: str,
    event_type: ProposalMemoEventType,
    actor_id: str,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
    reason: dict[str, Any],
) -> tuple[ProposalMemoEventRecord, bool]:
    if idempotency_key:
        replayed = _find_replayed_event(
            repository=repository,
            memo=memo,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replayed is not None:
            return replayed, True
    event = ProposalMemoEventRecord(
        event_id=event_id,
        memo_id=memo.memo_id,
        proposal_id=memo.proposal_id,
        proposal_version_no=memo.proposal_version_no,
        event_type=event_type,
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json={
            **reason,
            "memo_hash": memo.memo_hash,
            "source_input_hash": memo.source_input_hash,
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
        },
    )
    repository.append_memo_event(event)
    return event, False


def _find_replayed_event(
    *,
    repository: ProposalRepository,
    memo: ProposalMemoRecord,
    idempotency_key: str,
    request_hash: str,
) -> ProposalMemoEventRecord | None:
    for event in repository.list_memo_events(memo_id=memo.memo_id):
        if event.reason_json.get("idempotency_key") != idempotency_key:
            continue
        if event.reason_json.get("idempotency_request_hash") != request_hash:
            raise ProposalIdempotencyConflictError("MEMO_EVENT_IDEMPOTENCY_KEY_CONFLICT")
        return event
    return None


def _to_audit_event(event: ProposalMemoEventRecord) -> ProposalMemoAuditEvent:
    return ProposalMemoAuditEvent(
        event_id=event.event_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        occurred_at=event.occurred_at.isoformat(),
        reason=dict(event.reason_json),
    )


def _latest_event_posture(
    events: list[ProposalMemoEventRecord],
    *,
    event_type: str,
) -> dict[str, Any]:
    matching = [event for event in events if event.event_type == event_type]
    if not matching:
        return {"status": "NOT_RECORDED"}
    latest = matching[-1]
    return {
        "status": "RECORDED",
        "event_id": latest.event_id,
        "actor_id": latest.actor_id,
        "occurred_at": latest.occurred_at.isoformat(),
        **dict(latest.reason_json),
    }


def _project_sections(memo_json: dict[str, Any], *, audience: str | None) -> list[dict[str, Any]]:
    sections = memo_json.get("sections")
    if not isinstance(sections, list):
        return []
    projected = [section for section in sections if isinstance(section, dict)]
    if audience is None:
        return projected
    return [section for section in projected if audience in section.get("audience_visibility", [])]


def _validate_source_memo_hash(*, memo: ProposalMemoRecord, source_memo_hash: str) -> None:
    if source_memo_hash != memo.memo_hash:
        raise ProposalValidationError("MEMO_SOURCE_HASH_MISMATCH")


def _request_hash(payload: dict[str, Any]) -> str:
    return str(hash_canonical_payload(payload))


def _memo_has_replay_metadata(memo: ProposalMemoRecord) -> bool:
    required = {
        "proposal_request_hash",
        "proposal_artifact_hash",
        "proposal_simulation_hash",
        "memo_source_input_hash",
        "memo_request_hash",
        "replay_policy",
    }
    return required.issubset(set(memo.replay_metadata_json))


def _raise_api_error(exc: ProposalMemoPersistenceError) -> None:
    message = str(exc)
    if "IDEMPOTENCY" in message and "CONFLICT" in message:
        raise ProposalIdempotencyConflictError(message) from exc
    raise ProposalValidationError(message) from exc
