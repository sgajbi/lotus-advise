from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from src.core.advisory_copilot.persistence_results import AdvisoryCopilotReviewResult
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.request_hashing import canonical_json_hash, stable_copilot_reason
from src.core.advisory_copilot.review import CopilotReviewAction, review_posture_for_action
from src.core.advisory_copilot.review_authority import (
    CopilotReviewPrincipal,
    copilot_review_audit_reason,
    validate_copilot_review_authority,
)
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_lineage import stable_copilot_record_id
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.structured_payload import assert_safe_structured_payload
from src.core.common.idempotency import normalize_optional_idempotency_key


def record_advisory_copilot_review(
    *,
    repository: AdvisoryCopilotRepository,
    run_id: str,
    action: CopilotReviewAction,
    principal: CopilotReviewPrincipal,
    submitted_actor_id: str | None,
    reason: dict[str, Any],
    correlation_id: str,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
) -> AdvisoryCopilotReviewResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    assert_safe_structured_payload(reason)
    run = repository.get_run(tenant_id=principal.tenant_id, run_id=run_id)
    if run is None:
        raise ValueError("COPILOT_RUN_NOT_FOUND")
    validate_copilot_review_authority(
        principal=principal,
        run=run,
        submitted_actor_id=submitted_actor_id,
    )
    audit_reason = copilot_review_audit_reason(
        reason,
        principal=principal,
        action=action,
    )

    now = occurred_at or datetime.now(timezone.utc)
    request_hash = _review_request_hash(
        run_id=run_id,
        tenant_id=principal.tenant_id,
        action=action,
        actor_id=principal.actor_id,
        reason=audit_reason,
    )
    review = _build_review_record(
        run=run,
        action=action,
        actor_id=principal.actor_id,
        reason=audit_reason,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        occurred_at=now,
    )
    updated_run = _run_with_review_posture(run=run, review=review, occurred_at=now)
    persisted_run, persisted_review, replayed = repository.transition_review(
        expected_run=run,
        updated_run=updated_run,
        review=review,
    )
    return AdvisoryCopilotReviewResult(
        run=persisted_run,
        review=persisted_review,
        replayed=replayed,
    )


def list_advisory_copilot_reviews(
    *, repository: AdvisoryCopilotRepository, tenant_id: str, run_id: str
) -> tuple[AdvisoryCopilotReviewRecord, ...]:
    return tuple(repository.list_reviews(tenant_id=tenant_id, run_id=run_id))


def _review_request_hash(
    *,
    run_id: str,
    tenant_id: str,
    action: CopilotReviewAction,
    actor_id: str,
    reason: dict[str, Any],
) -> str:
    return cast(
        str,
        canonical_json_hash(
            {
                "run_id": run_id,
                "action": action,
                "actor_id": actor_id,
                "reason": stable_copilot_reason(reason),
            }
        ),
    )


def _build_review_record(
    *,
    run: AdvisoryCopilotRunRecord,
    action: CopilotReviewAction,
    actor_id: str,
    reason: dict[str, Any],
    correlation_id: str,
    idempotency_key: str | None,
    request_hash: str,
    occurred_at: datetime,
) -> AdvisoryCopilotReviewRecord:
    return AdvisoryCopilotReviewRecord(
        review_id=stable_copilot_record_id(prefix="copilot_review", value=request_hash),
        run_id=run.run_id,
        tenant_id=run.tenant_id,
        action=action,
        previous_posture=run.review_posture,
        new_posture=review_posture_for_action(action),
        actor_id=actor_id,
        occurred_at=occurred_at,
        reason_json=dict(reason),
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )


def _run_with_review_posture(
    *,
    run: AdvisoryCopilotRunRecord,
    review: AdvisoryCopilotReviewRecord,
    occurred_at: datetime,
) -> AdvisoryCopilotRunRecord:
    return cast(
        AdvisoryCopilotRunRecord,
        run.model_copy(
            update={
                "review_posture": review.new_posture,
                "updated_at": occurred_at,
            }
        ),
    )
