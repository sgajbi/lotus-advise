from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.core.advisory_copilot.persistence_results import AdvisoryCopilotReviewResult
from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.request_hashing import canonical_json_hash
from src.core.advisory_copilot.review import (
    CopilotReviewAction,
    is_terminal_review_posture,
    review_posture_for_action,
)
from src.core.advisory_copilot.review_records import AdvisoryCopilotReviewRecord
from src.core.advisory_copilot.run_lineage import stable_copilot_record_id
from src.core.advisory_copilot.structured_payload import assert_safe_structured_payload
from src.core.common.idempotency import normalize_optional_idempotency_key


def record_advisory_copilot_review(
    *,
    repository: AdvisoryCopilotRepository,
    run_id: str,
    action: CopilotReviewAction,
    actor_id: str,
    reason: dict[str, Any],
    correlation_id: str,
    idempotency_key: str | None = None,
    occurred_at: datetime | None = None,
) -> AdvisoryCopilotReviewResult:
    idempotency_key = normalize_optional_idempotency_key(idempotency_key)
    assert_safe_structured_payload(reason)
    run = repository.get_run(run_id=run_id)
    if run is None:
        raise ValueError("COPILOT_RUN_NOT_FOUND")

    now = occurred_at or datetime.now(timezone.utc)
    review_request = {
        "run_id": run_id,
        "action": action,
        "actor_id": actor_id,
        "reason": reason,
    }
    request_hash = canonical_json_hash(review_request)
    if idempotency_key:
        existing_review = repository.get_review_by_idempotency(
            run_id=run_id,
            idempotency_key=idempotency_key,
        )
        if existing_review is not None:
            if existing_review.request_hash != request_hash:
                raise ValueError("COPILOT_REVIEW_IDEMPOTENCY_KEY_CONFLICT")
            replayed_run = repository.get_run(run_id=run_id)
            if replayed_run is None:
                raise ValueError("COPILOT_REVIEW_RECORD_ORPHANED")
            return AdvisoryCopilotReviewResult(
                run=replayed_run,
                review=existing_review,
                replayed=True,
            )

    if is_terminal_review_posture(run.review_posture):
        raise ValueError("COPILOT_RUN_REVIEW_POSTURE_TERMINAL")

    new_posture = review_posture_for_action(action)
    review = AdvisoryCopilotReviewRecord(
        review_id=stable_copilot_record_id(prefix="copilot_review", value=request_hash),
        run_id=run_id,
        action=action,
        previous_posture=run.review_posture,
        new_posture=new_posture,
        actor_id=actor_id,
        occurred_at=now,
        reason_json=dict(reason),
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    updated_run = run.model_copy(update={"review_posture": new_posture, "updated_at": now})
    repository.append_review(review)
    repository.update_run(updated_run)
    return AdvisoryCopilotReviewResult(run=updated_run, review=review, replayed=False)


def list_advisory_copilot_reviews(
    *, repository: AdvisoryCopilotRepository, run_id: str
) -> tuple[AdvisoryCopilotReviewRecord, ...]:
    return tuple(repository.list_reviews(run_id=run_id))
