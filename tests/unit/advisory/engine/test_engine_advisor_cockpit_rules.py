from __future__ import annotations

from datetime import UTC, datetime

from src.core.advisor_cockpit import (
    CRITICAL_OVERDUE_WINDOW,
    DUE_NOW_GRACE_WINDOW,
    DUE_SOON_WINDOW,
    OWNER_BLOCKING_STATUSES,
    CockpitAcknowledgementState,
    PolicyReviewActionSource,
    apply_cockpit_acknowledgement_state,
    build_policy_review_required_action,
    derive_cockpit_sla_age_band,
    is_cockpit_action_owner_blocking,
    with_cockpit_sla_age_band,
)

NOW = datetime(2026, 5, 27, 8, 0, tzinfo=UTC)


def test_sla_and_owner_blocking_rule_constants_are_backend_owned() -> None:
    assert DUE_SOON_WINDOW.total_seconds() == 24 * 60 * 60
    assert DUE_NOW_GRACE_WINDOW.total_seconds() == 60 * 60
    assert CRITICAL_OVERDUE_WINDOW.total_seconds() == 24 * 60 * 60
    assert OWNER_BLOCKING_STATUSES == frozenset({"BLOCKED", "PENDING_REVIEW", "HANDOFF_REQUESTED"})


def _policy_action():
    return build_policy_review_required_action(
        PolicyReviewActionSource(
            policy_evaluation_id="policy_eval_sg_001",
            portfolio_id="PB_SG_GLOBAL_BAL_001",
            proposal_id="proposal_sg_001",
            policy_result="PENDING_REVIEW",
            due_at="2026-05-27T07:30:00+00:00",
        )
    )


def test_sla_age_band_is_deterministic_from_due_time() -> None:
    assert derive_cockpit_sla_age_band(due_at=None, now=NOW) == "NOT_APPLICABLE"
    assert derive_cockpit_sla_age_band(due_at="2026-05-29T09:00:00+00:00", now=NOW) == "NOT_DUE"
    assert derive_cockpit_sla_age_band(due_at="2026-05-28T07:59:00+00:00", now=NOW) == "DUE_SOON"
    assert derive_cockpit_sla_age_band(due_at="2026-05-27T07:30:00+00:00", now=NOW) == "DUE_NOW"
    assert (
        derive_cockpit_sla_age_band(due_at="2026-05-26T07:59:00+00:00", now=NOW)
        == "CRITICAL_OVERDUE"
    )
    assert derive_cockpit_sla_age_band(due_at="2026-05-26T20:00:00+00:00", now=NOW) == "OVERDUE"


def test_sla_age_band_preserves_threshold_boundaries() -> None:
    assert derive_cockpit_sla_age_band(due_at="2026-05-28T08:00:01+00:00", now=NOW) == "NOT_DUE"
    assert derive_cockpit_sla_age_band(due_at="2026-05-28T08:00:00+00:00", now=NOW) == "DUE_SOON"
    assert derive_cockpit_sla_age_band(due_at="2026-05-27T08:00:00+00:00", now=NOW) == "DUE_NOW"
    assert derive_cockpit_sla_age_band(due_at="2026-05-27T07:00:00+00:00", now=NOW) == "DUE_NOW"
    assert derive_cockpit_sla_age_band(due_at="2026-05-27T06:59:59+00:00", now=NOW) == "OVERDUE"
    assert derive_cockpit_sla_age_band(due_at="2026-05-26T08:00:01+00:00", now=NOW) == "OVERDUE"
    assert (
        derive_cockpit_sla_age_band(due_at="2026-05-26T08:00:00+00:00", now=NOW)
        == "CRITICAL_OVERDUE"
    )


def test_sla_age_band_normalizes_zulu_and_naive_datetimes_to_utc() -> None:
    naive_now = datetime(2026, 5, 27, 8, 0)

    assert derive_cockpit_sla_age_band(due_at="2026-05-27T08:30:00Z", now=naive_now) == "DUE_SOON"
    assert derive_cockpit_sla_age_band(due_at="2026-05-27T07:30:00Z", now=naive_now) == "DUE_NOW"


def test_sla_age_band_can_be_applied_without_changing_action_identity() -> None:
    action = _policy_action()

    updated = with_cockpit_sla_age_band(action, now=NOW)

    assert updated.action_item_id == action.action_item_id
    assert updated.status == "PENDING_REVIEW"
    assert updated.priority == "HIGH"
    assert updated.sla_age_band == "DUE_NOW"


def test_acknowledgement_does_not_clear_owner_blocking_posture() -> None:
    action = _policy_action()
    acknowledgement = CockpitAcknowledgementState(
        acknowledged=True,
        acknowledgement_id="ack_sg_001",
        acknowledged_by="advisor_sg_001",
        acknowledged_at="2026-05-27T08:05:00+00:00",
        acknowledgement_note="Advisor reviewed the pending policy action.",
    )

    acknowledged = apply_cockpit_acknowledgement_state(action, acknowledgement)

    assert acknowledged.acknowledgement_state.acknowledged is True
    assert acknowledged.status == "PENDING_REVIEW"
    assert acknowledged.priority == "HIGH"
    assert acknowledged.owner_role == "COMPLIANCE_REVIEWER"
    assert is_cockpit_action_owner_blocking(acknowledged) is True


def test_completed_and_superseded_actions_are_not_owner_blocking() -> None:
    action = _policy_action()

    assert (
        is_cockpit_action_owner_blocking(action.model_copy(update={"status": "COMPLETED"})) is False
    )
    assert (
        is_cockpit_action_owner_blocking(action.model_copy(update={"status": "SUPERSEDED"}))
        is False
    )
