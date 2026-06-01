from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from src.core.advisor_cockpit.action_models import AdvisoryActionItem
from src.core.advisor_cockpit.reference_models import CockpitAcknowledgementState
from src.core.advisor_cockpit.type_models import AdvisorCockpitSlaAgeBand

DUE_SOON_WINDOW = timedelta(hours=24)
DUE_NOW_GRACE_WINDOW = timedelta(hours=1)
CRITICAL_OVERDUE_WINDOW = timedelta(hours=24)
OWNER_BLOCKING_STATUSES = frozenset({"BLOCKED", "PENDING_REVIEW", "HANDOFF_REQUESTED"})


def derive_cockpit_sla_age_band(
    *,
    due_at: str | None,
    now: datetime,
) -> AdvisorCockpitSlaAgeBand:
    if not due_at:
        return "NOT_APPLICABLE"

    due = _parse_utc(due_at)
    current = _ensure_utc(now)
    delta = due - current
    if delta > DUE_SOON_WINDOW:
        return "NOT_DUE"
    if delta > timedelta(0):
        return "DUE_SOON"
    if delta >= -DUE_NOW_GRACE_WINDOW:
        return "DUE_NOW"
    if delta <= -CRITICAL_OVERDUE_WINDOW:
        return "CRITICAL_OVERDUE"
    return "OVERDUE"


def with_cockpit_sla_age_band(
    action: AdvisoryActionItem,
    *,
    now: datetime,
) -> AdvisoryActionItem:
    return cast(
        AdvisoryActionItem,
        action.model_copy(
            update={"sla_age_band": derive_cockpit_sla_age_band(due_at=action.due_at, now=now)}
        ),
    )


def apply_cockpit_acknowledgement_state(
    action: AdvisoryActionItem,
    acknowledgement_state: CockpitAcknowledgementState,
) -> AdvisoryActionItem:
    return cast(
        AdvisoryActionItem,
        action.model_copy(update={"acknowledgement_state": acknowledgement_state}),
    )


def is_cockpit_action_owner_blocking(action: AdvisoryActionItem) -> bool:
    return action.status in OWNER_BLOCKING_STATUSES


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _ensure_utc(parsed)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
