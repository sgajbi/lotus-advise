from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel, Field

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.memo_builder import build_advisory_proposal_memo_evidence_pack
from src.core.proposals.models import (
    ProposalMemoEventRecord,
    ProposalMemoIdempotencyRecord,
    ProposalMemoLifecycleStatus,
    ProposalMemoRecord,
    ProposalVersionRecord,
)
from src.core.proposals.repository import ProposalRepository


class ProposalMemoPersistenceError(ValueError):
    pass


class ProposalMemoPersistenceResult(BaseModel):
    memo: ProposalMemoRecord = Field(description="Persisted memo record.")
    created: bool = Field(description="Whether this call created the memo.")
    replayed: bool = Field(description="Whether this call replayed an idempotent memo request.")
    audit_event: ProposalMemoEventRecord | None = Field(
        default=None,
        description="Audit event created for a new memo record.",
    )


def build_memo_persistence_request_hash(
    *,
    version: ProposalVersionRecord,
    lifecycle_status: str,
    reason: dict[str, Any] | None = None,
) -> str:
    return cast(
        str,
        hash_canonical_payload(
            {
                "proposal_id": version.proposal_id,
                "proposal_version_no": version.version_no,
                "proposal_version_id": version.proposal_version_id,
                "artifact_hash": version.artifact_hash,
                "simulation_hash": version.simulation_hash,
                "request_hash": version.request_hash,
                "evidence_bundle_hash": hash_canonical_payload(version.evidence_bundle_json),
                "lifecycle_status": lifecycle_status,
                "reason": reason or {},
            }
        ),
    )


def create_or_replay_proposal_memo(
    *,
    repository: ProposalRepository,
    version: ProposalVersionRecord,
    idempotency_key: str | None,
    created_by: str,
    created_at: datetime,
    event_id: str,
    lifecycle_status: str = "DRAFT",
    reason: dict[str, Any] | None = None,
) -> ProposalMemoPersistenceResult:
    memo_lifecycle_status = _memo_lifecycle_status(lifecycle_status)
    request_hash = build_memo_persistence_request_hash(
        version=version,
        lifecycle_status=memo_lifecycle_status,
        reason=reason,
    )
    replay_result = _replay_memo_result(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replay_result is not None:
        return replay_result
    existing = repository.get_memo_by_proposal_version(
        proposal_id=version.proposal_id,
        proposal_version_no=version.version_no,
    )
    if existing is not None:
        return _existing_memo_result(
            repository=repository,
            existing=existing,
            version=version,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            created_at=created_at,
        )
    return _create_memo_result(
        repository=repository,
        version=version,
        lifecycle_status=memo_lifecycle_status,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        created_by=created_by,
        created_at=created_at,
        event_id=event_id,
        reason=reason,
    )


def _memo_lifecycle_status(lifecycle_status: str) -> ProposalMemoLifecycleStatus:
    if lifecycle_status not in {"DRAFT", "FINALIZED"}:
        raise ProposalMemoPersistenceError("MEMO_LIFECYCLE_STATUS_UNSUPPORTED")
    return cast(ProposalMemoLifecycleStatus, lifecycle_status)


def _replay_memo_result(
    *,
    repository: ProposalRepository,
    idempotency_key: str | None,
    request_hash: str,
) -> ProposalMemoPersistenceResult | None:
    if not idempotency_key:
        return None
    replayed = _find_replayed_memo(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    if replayed is None:
        return None
    return ProposalMemoPersistenceResult(
        memo=replayed,
        created=False,
        replayed=True,
        audit_event=None,
    )


def _existing_memo_result(
    *,
    repository: ProposalRepository,
    existing: ProposalMemoRecord,
    version: ProposalVersionRecord,
    idempotency_key: str | None,
    request_hash: str,
    created_at: datetime,
) -> ProposalMemoPersistenceResult:
    _ensure_existing_source_is_identical(existing=existing, version=version)
    _save_memo_idempotency(
        repository=repository,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        memo=existing,
        created_at=created_at,
    )
    return ProposalMemoPersistenceResult(
        memo=existing,
        created=False,
        replayed=False,
        audit_event=None,
    )


def _create_memo_result(
    *,
    repository: ProposalRepository,
    version: ProposalVersionRecord,
    lifecycle_status: ProposalMemoLifecycleStatus,
    idempotency_key: str | None,
    request_hash: str,
    created_by: str,
    created_at: datetime,
    event_id: str,
    reason: dict[str, Any] | None,
) -> ProposalMemoPersistenceResult:
    memo_record = _build_memo_record(
        version=version,
        created_by=created_by,
        created_at=created_at,
        lifecycle_status=lifecycle_status,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        reason=reason,
    )
    event = _created_event(
        event_id=event_id,
        memo=memo_record,
        actor_id=created_by,
        occurred_at=created_at,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        reason=reason,
    )
    idempotency = _optional_idempotency_record(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        memo=memo_record,
        created_at=created_at,
    )
    repository.create_memo_with_idempotency_event(
        memo=memo_record,
        idempotency=idempotency,
        event=event,
    )
    return ProposalMemoPersistenceResult(
        memo=memo_record,
        created=True,
        replayed=False,
        audit_event=event,
    )


def _save_memo_idempotency(
    *,
    repository: ProposalRepository,
    idempotency_key: str | None,
    request_hash: str,
    memo: ProposalMemoRecord,
    created_at: datetime,
) -> None:
    if idempotency_key:
        repository.save_memo_idempotency(
            _idempotency_record(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                memo=memo,
                created_at=created_at,
            )
        )


def _optional_idempotency_record(
    *,
    idempotency_key: str | None,
    request_hash: str,
    memo: ProposalMemoRecord,
    created_at: datetime,
) -> ProposalMemoIdempotencyRecord | None:
    if not idempotency_key:
        return None
    return _idempotency_record(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        memo=memo,
        created_at=created_at,
    )


def _find_replayed_memo(
    *,
    repository: ProposalRepository,
    idempotency_key: str,
    request_hash: str,
) -> ProposalMemoRecord | None:
    existing_key = repository.get_memo_idempotency(idempotency_key=idempotency_key)
    if existing_key is None:
        return None
    if existing_key.request_hash != request_hash:
        raise ProposalMemoPersistenceError("MEMO_IDEMPOTENCY_KEY_CONFLICT")
    memo = repository.get_memo(memo_id=existing_key.memo_id)
    if memo is None:
        raise ProposalMemoPersistenceError("MEMO_IDEMPOTENCY_RECORD_ORPHANED")
    return memo


def _build_memo_record(
    *,
    version: ProposalVersionRecord,
    created_by: str,
    created_at: datetime,
    lifecycle_status: ProposalMemoLifecycleStatus,
    idempotency_key: str | None,
    request_hash: str,
    reason: dict[str, Any] | None,
) -> ProposalMemoRecord:
    evidence_bundle = deepcopy(version.evidence_bundle_json)
    pack = build_advisory_proposal_memo_evidence_pack(
        proposal_id=version.proposal_id,
        proposal_version_no=version.version_no,
        proposal_version_id=version.proposal_version_id,
        artifact_json=deepcopy(version.artifact_json),
        evidence_bundle=evidence_bundle,
    )
    if lifecycle_status == "FINALIZED" and pack.status != "READY":
        raise ProposalMemoPersistenceError("MEMO_FINALIZATION_BLOCKED_BY_EVIDENCE_POSTURE")
    memo_json = pack.model_dump(mode="json")
    replay_metadata: dict[str, Any] = {
        "proposal_request_hash": version.request_hash,
        "proposal_artifact_hash": version.artifact_hash,
        "proposal_simulation_hash": version.simulation_hash,
        "memo_source_input_hash": pack.source_input_hash,
        "memo_request_hash": request_hash,
        "idempotency_key": idempotency_key,
        "creation_reason": reason or {},
        "replay_policy": "EXACT_SOURCE_HASH_MATCH",
    }
    return ProposalMemoRecord(
        memo_id=pack.memo_id,
        proposal_id=version.proposal_id,
        proposal_version_no=version.version_no,
        proposal_version_id=version.proposal_version_id,
        artifact_id=pack.artifact_id,
        memo_version=pack.memo_version,
        memo_status=pack.status,
        lifecycle_status=lifecycle_status,
        created_by=created_by,
        created_at=created_at,
        source_input_hash=pack.source_input_hash,
        memo_hash=pack.memo_hash,
        memo_json=memo_json,
        projection_json=deepcopy(pack.projection_policy),
        review_events_json=[],
        report_package_events_json=[],
        archive_refs_json=[],
        ai_refs_json=[],
        replay_metadata_json=replay_metadata,
    )


def _ensure_existing_source_is_identical(
    *,
    existing: ProposalMemoRecord,
    version: ProposalVersionRecord,
) -> None:
    if existing.replay_metadata_json.get("proposal_artifact_hash") != version.artifact_hash:
        raise ProposalMemoPersistenceError("MEMO_SOURCE_ARTIFACT_HASH_CONFLICT")
    if existing.replay_metadata_json.get("proposal_simulation_hash") != version.simulation_hash:
        raise ProposalMemoPersistenceError("MEMO_SOURCE_SIMULATION_HASH_CONFLICT")


def _idempotency_record(
    *,
    idempotency_key: str,
    request_hash: str,
    memo: ProposalMemoRecord,
    created_at: datetime,
) -> ProposalMemoIdempotencyRecord:
    return ProposalMemoIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        memo_id=memo.memo_id,
        proposal_id=memo.proposal_id,
        proposal_version_no=memo.proposal_version_no,
        created_at=created_at,
    )


def _created_event(
    *,
    event_id: str,
    memo: ProposalMemoRecord,
    actor_id: str,
    occurred_at: datetime,
    idempotency_key: str | None,
    request_hash: str,
    reason: dict[str, Any] | None,
) -> ProposalMemoEventRecord:
    return ProposalMemoEventRecord(
        event_id=event_id,
        memo_id=memo.memo_id,
        proposal_id=memo.proposal_id,
        proposal_version_no=memo.proposal_version_no,
        event_type="MEMO_DRAFT_CREATED" if memo.lifecycle_status == "DRAFT" else "MEMO_FINALIZED",
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json={
            "memo_hash": memo.memo_hash,
            "source_input_hash": memo.source_input_hash,
            "memo_status": memo.memo_status,
            "lifecycle_status": memo.lifecycle_status,
            "idempotency_key": idempotency_key,
            "idempotency_request_hash": request_hash,
            "creation_reason": reason or {},
        },
    )
