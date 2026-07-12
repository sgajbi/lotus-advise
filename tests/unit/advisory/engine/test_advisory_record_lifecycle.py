from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.record_lifecycle import (
    ADVISORY_RECORD_RETENTION_POLICIES,
    AdvisoryRecordLifecycleState,
    build_legal_hold_audit_event,
    evaluate_advisory_record_purge,
)


def _record(
    *,
    retention_expires_at: datetime | None = None,
    legal_hold: bool = False,
    dependent_record_refs: tuple[str, ...] = (),
    tombstoned: bool = False,
) -> AdvisoryRecordLifecycleState:
    return AdvisoryRecordLifecycleState(
        record_family="ADVISORY_COPILOT_RUN",
        record_id="copilot_run_sensitive_001",
        retention_class="ADVISORY_REVIEW_RECORD",
        retention_expires_at=retention_expires_at,
        legal_hold=legal_hold,
        dependent_record_refs=dependent_record_refs,
        tombstoned=tombstoned,
    )


def test_advisory_record_retention_policies_cover_required_record_families() -> None:
    assert set(ADVISORY_RECORD_RETENTION_POLICIES) == {
        "PROPOSAL_VERSION",
        "PROPOSAL_LIFECYCLE_EVENT",
        "PROPOSAL_APPROVAL",
        "POLICY_EVALUATION",
        "REPORT_REQUEST",
        "ADVISORY_COPILOT_EVIDENCE_PACKET",
        "ADVISORY_COPILOT_RUN",
        "ADVISORY_COPILOT_REVIEW",
    }
    assert all(
        policy.jurisdiction_period_source == "approved-bank-policy-required"
        for policy in ADVISORY_RECORD_RETENTION_POLICIES.values()
    )
    assert all(
        policy.immutable_correction_model.startswith("append")
        or policy.immutable_correction_model.startswith("rebuild_packet")
        for policy in ADVISORY_RECORD_RETENTION_POLICIES.values()
    )


def test_legal_hold_blocks_purge_and_records_sanitized_audit() -> None:
    as_of = datetime(2034, 1, 1, tzinfo=timezone.utc)
    record = _record(
        retention_expires_at=as_of - timedelta(days=1),
        legal_hold=True,
    )

    decision = evaluate_advisory_record_purge(
        record=record,
        as_of=as_of,
        authorized=True,
        requested_by="advisor_sensitive_001",
        idempotency_key="purge-sensitive-001",
    )
    audit_event = build_legal_hold_audit_event(
        record=record,
        action="APPLY_HOLD",
        actor_id="legal_sensitive_actor",
        reason="litigation sensitive reason",
        occurred_at=as_of,
    )

    assert decision.eligible is False
    assert decision.reason_code == "PURGE_BLOCKED_BY_LEGAL_HOLD"
    assert decision.audit_event["legal_hold"] is True
    assert audit_event["append_only"] is True
    assert "copilot_run_sensitive_001" not in str(decision.audit_event)
    assert "legal_sensitive_actor" not in str(audit_event)
    assert "litigation sensitive reason" not in str(audit_event)


def test_expired_authorized_record_is_purge_eligible_with_tombstone_audit() -> None:
    as_of = datetime(2034, 1, 1, tzinfo=timezone.utc)

    decision = evaluate_advisory_record_purge(
        record=_record(retention_expires_at=as_of - timedelta(seconds=1)),
        as_of=as_of,
        authorized=True,
        requested_by="records_officer_001",
        idempotency_key="purge-eligible-001",
    )

    assert decision.eligible is True
    assert decision.reason_code == "PURGE_ELIGIBLE"
    assert decision.audit_event["tombstone_required"] is True
    assert decision.audit_event["policy_owner"] == "advisory-copilot"
    assert decision.audit_event["policy_retention_class"] == "ADVISORY_REVIEW_RECORD"
    assert "records_officer_001" not in str(decision.audit_event)


def test_purge_refuses_unexpired_unauthorized_dependent_or_tombstoned_records() -> None:
    as_of = datetime(2034, 1, 1, tzinfo=timezone.utc)
    active = _record(retention_expires_at=as_of + timedelta(days=1))
    dependent = _record(
        retention_expires_at=as_of - timedelta(days=1),
        dependent_record_refs=("copilot_review_001",),
    )
    tombstoned = _record(
        retention_expires_at=as_of - timedelta(days=1),
        tombstoned=True,
    )

    unauthorized_decision = evaluate_advisory_record_purge(
        record=_record(retention_expires_at=as_of - timedelta(days=1)),
        as_of=as_of,
        authorized=False,
        requested_by="records_officer_001",
        idempotency_key="purge-unauthorized-001",
    )
    active_decision = evaluate_advisory_record_purge(
        record=active,
        as_of=as_of,
        authorized=True,
        requested_by="records_officer_001",
        idempotency_key="purge-active-001",
    )
    dependent_decision = evaluate_advisory_record_purge(
        record=dependent,
        as_of=as_of,
        authorized=True,
        requested_by="records_officer_001",
        idempotency_key="purge-dependent-001",
    )
    tombstoned_decision = evaluate_advisory_record_purge(
        record=tombstoned,
        as_of=as_of,
        authorized=True,
        requested_by="records_officer_001",
        idempotency_key="purge-tombstoned-001",
    )

    assert unauthorized_decision.reason_code == "PURGE_NOT_AUTHORIZED"
    assert active_decision.reason_code == "PURGE_BLOCKED_BY_RETENTION"
    assert dependent_decision.reason_code == "PURGE_BLOCKED_BY_DEPENDENCIES"
    assert dependent_decision.audit_event["dependent_record_count"] == 1
    assert tombstoned_decision.reason_code == "PURGE_ALREADY_TOMBSTONED"
