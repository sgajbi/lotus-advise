from __future__ import annotations

from src.core.advisory_copilot.repository import AdvisoryCopilotRepository
from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.run_review_policy import can_attempt_advisory_copilot_run_refresh


def resolve_advisory_copilot_run_replay(
    *,
    repository: AdvisoryCopilotRepository,
    idempotency_key: str | None,
    request_hash: str,
) -> AdvisoryCopilotRunRecord | None:
    if not idempotency_key:
        return None
    existing_idempotency = repository.get_run_idempotency(idempotency_key=idempotency_key)
    if existing_idempotency is None:
        return None
    if existing_idempotency.request_hash != request_hash:
        raise ValueError("COPILOT_RUN_IDEMPOTENCY_KEY_CONFLICT")
    existing_run = repository.get_run(run_id=existing_idempotency.run_id)
    if existing_run is None:
        raise ValueError("COPILOT_RUN_IDEMPOTENCY_RECORD_ORPHANED")
    if can_attempt_advisory_copilot_run_refresh(existing_run):
        return None
    return existing_run
