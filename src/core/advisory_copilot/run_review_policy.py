from __future__ import annotations

from src.core.advisory_copilot.run_records import AdvisoryCopilotRunRecord
from src.core.advisory_copilot.type_models import CopilotReviewPosture


def review_posture_from_draft_status(status: str) -> CopilotReviewPosture:
    allowed: set[CopilotReviewPosture] = {
        "REVIEW_REQUIRED",
        "APPROVED_FOR_INTERNAL_USE",
        "REJECTED",
        "SUPERSEDED",
        "EXPIRED",
        "UNSUPPORTED",
        "GUARDRAIL_REJECTED",
        "UNAVAILABLE",
    }
    return status if status in allowed else "REVIEW_REQUIRED"  # type: ignore[return-value]


def can_refresh_retryable_copilot_run(
    *,
    existing_run: AdvisoryCopilotRunRecord,
    incoming_review_posture: CopilotReviewPosture,
) -> bool:
    if not can_attempt_advisory_copilot_run_refresh(existing_run):
        return False
    if existing_run.review_posture == "UNAVAILABLE" and incoming_review_posture != "UNAVAILABLE":
        return True
    return bool(
        existing_run.review_posture == "GUARDRAIL_REJECTED"
        and incoming_review_posture == "REVIEW_REQUIRED"
    )


def can_attempt_advisory_copilot_run_refresh(existing_run: AdvisoryCopilotRunRecord) -> bool:
    fallback_reason = existing_run.lineage_json.get("fallback_reason")
    if existing_run.review_posture == "UNAVAILABLE":
        return fallback_reason is not None
    return bool(
        existing_run.review_posture == "GUARDRAIL_REJECTED"
        and fallback_reason == "COPILOT_OUTPUT_GUARDRAIL_REJECTED"
    )
