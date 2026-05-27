from __future__ import annotations

from src.core.advisor_cockpit.models import AdvisoryActionItem

COCKPIT_PRIORITY_RANK: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFORMATIONAL": 4,
}
COCKPIT_SLA_AGE_RANK: dict[str, int] = {
    "CRITICAL_OVERDUE": 0,
    "OVERDUE": 1,
    "DUE_NOW": 2,
    "DUE_SOON": 3,
    "NOT_DUE": 4,
    "NOT_APPLICABLE": 5,
}
COCKPIT_STATUS_RANK: dict[str, int] = {
    "BLOCKED": 0,
    "PENDING_REVIEW": 1,
    "READY": 2,
    "HANDOFF_REQUESTED": 3,
    "ACKNOWLEDGED": 4,
    "COMPLETED": 5,
    "SUPERSEDED": 6,
}
COCKPIT_ACTION_FAMILY_RANK: dict[str, int] = {
    "POLICY_REVIEW_REQUIRED": 0,
    "APPROVAL_DEPENDENCY_AGING": 1,
    "CLIENT_CONSENT_REQUIRED": 2,
    "MEMO_PACKAGE_BLOCKED": 3,
    "REPORT_RENDER_ARCHIVE_BLOCKED": 4,
    "CLIENT_MEETING_PREPARATION": 5,
    "PROPOSAL_READY_FOR_REVIEW": 6,
    "PROPOSAL_BLOCKED_BY_SOURCE_GAP": 7,
    "EXECUTION_HANDOFF_READY": 8,
    "EXECUTION_STATUS_ATTENTION": 9,
    "HOUSE_VIEW_IMPACT_REVIEW": 10,
    "WORKSPACE_DRAFT_STALE": 11,
    "CLIENT_FOLLOW_UP_REQUIRED": 12,
    "SUPPORTABILITY_DEGRADED": 13,
    "UNSUPPORTED_CAPABILITY": 14,
}


def cockpit_action_sort_key(action: AdvisoryActionItem) -> tuple[int, str, int, int, int, str, str]:
    return (
        COCKPIT_PRIORITY_RANK[action.priority],
        action.due_at or "9999-12-31T23:59:59+00:00",
        COCKPIT_SLA_AGE_RANK[action.sla_age_band],
        -action.materiality_rank,
        COCKPIT_STATUS_RANK[action.status],
        f"{COCKPIT_ACTION_FAMILY_RANK[action.action_family]:02d}:{action.action_family}",
        action.action_item_id,
    )


def sort_cockpit_action_items(items: list[AdvisoryActionItem]) -> list[AdvisoryActionItem]:
    return sorted(items, key=cockpit_action_sort_key)
