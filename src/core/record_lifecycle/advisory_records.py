from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from src.core.common.canonical import hash_canonical_payload

AdvisoryRecordFamily = Literal[
    "PROPOSAL_VERSION",
    "PROPOSAL_LIFECYCLE_EVENT",
    "PROPOSAL_APPROVAL",
    "POLICY_EVALUATION",
    "REPORT_REQUEST",
    "ADVISORY_COPILOT_EVIDENCE_PACKET",
    "ADVISORY_COPILOT_RUN",
    "ADVISORY_COPILOT_REVIEW",
]


@dataclass(frozen=True)
class AdvisoryRecordRetentionPolicy:
    record_family: AdvisoryRecordFamily
    retention_class: str
    owner: str
    purge_policy: str
    immutable_correction_model: str
    legal_hold_supported: bool = True
    jurisdiction_period_source: str = "approved-bank-policy-required"


@dataclass(frozen=True)
class AdvisoryRecordLifecycleState:
    record_family: AdvisoryRecordFamily
    record_id: str
    retention_class: str
    retention_expires_at: datetime | None
    legal_hold: bool = False
    dependent_record_refs: tuple[str, ...] = ()
    tombstoned: bool = False


@dataclass(frozen=True)
class AdvisoryRecordPurgeDecision:
    eligible: bool
    reason_code: str
    audit_event: dict[str, object]


ADVISORY_RECORD_RETENTION_POLICIES: dict[AdvisoryRecordFamily, AdvisoryRecordRetentionPolicy] = {
    "PROPOSAL_VERSION": AdvisoryRecordRetentionPolicy(
        record_family="PROPOSAL_VERSION",
        retention_class="ADVISORY_PROPOSAL_RECORD",
        owner="proposal-lifecycle",
        purge_policy="tombstone_after_retention_expiry_unless_legal_hold_or_dependency",
        immutable_correction_model="append_compensating_version_or_lifecycle_event",
    ),
    "PROPOSAL_LIFECYCLE_EVENT": AdvisoryRecordRetentionPolicy(
        record_family="PROPOSAL_LIFECYCLE_EVENT",
        retention_class="ADVISORY_PROPOSAL_RECORD",
        owner="proposal-lifecycle",
        purge_policy="retain_append_only_event_until_parent_record_purge",
        immutable_correction_model="append_compensating_lifecycle_event",
    ),
    "PROPOSAL_APPROVAL": AdvisoryRecordRetentionPolicy(
        record_family="PROPOSAL_APPROVAL",
        retention_class="ADVISORY_PROPOSAL_RECORD",
        owner="proposal-lifecycle",
        purge_policy="retain_approval_audit_until_parent_record_purge",
        immutable_correction_model="append_compensating_approval_event",
    ),
    "POLICY_EVALUATION": AdvisoryRecordRetentionPolicy(
        record_family="POLICY_EVALUATION",
        retention_class="ADVISORY_POLICY_RECORD",
        owner="policy-packs",
        purge_policy="tombstone_after_retention_expiry_unless_legal_hold_or_dependency",
        immutable_correction_model="append_new_evaluation_or_signoff_event",
    ),
    "REPORT_REQUEST": AdvisoryRecordRetentionPolicy(
        record_family="REPORT_REQUEST",
        retention_class="ADVISORY_REPORT_REQUEST_RECORD",
        owner="proposal-reporting",
        purge_policy="retain_request_lineage_until_report_archive_policy_allows_purge",
        immutable_correction_model="append_compensating_report_request_event",
    ),
    "ADVISORY_COPILOT_EVIDENCE_PACKET": AdvisoryRecordRetentionPolicy(
        record_family="ADVISORY_COPILOT_EVIDENCE_PACKET",
        retention_class="ADVISORY_REVIEW_RECORD",
        owner="advisory-copilot",
        purge_policy="purge_with_copilot_interaction_unless_legal_hold",
        immutable_correction_model="rebuild_packet_with_new_hash_and_audit_reason",
    ),
    "ADVISORY_COPILOT_RUN": AdvisoryRecordRetentionPolicy(
        record_family="ADVISORY_COPILOT_RUN",
        retention_class="ADVISORY_REVIEW_RECORD",
        owner="advisory-copilot",
        purge_policy="tombstone_after_retention_expiry_unless_legal_hold_or_review_dependency",
        immutable_correction_model="append_new_run_or_review_event",
    ),
    "ADVISORY_COPILOT_REVIEW": AdvisoryRecordRetentionPolicy(
        record_family="ADVISORY_COPILOT_REVIEW",
        retention_class="ADVISORY_REVIEW_RECORD",
        owner="advisory-copilot",
        purge_policy="retain_review_audit_until_parent_run_purge",
        immutable_correction_model="append_compensating_review_event",
    ),
}


def advisory_record_retention_policy(
    record_family: AdvisoryRecordFamily,
) -> AdvisoryRecordRetentionPolicy:
    return ADVISORY_RECORD_RETENTION_POLICIES[record_family]


def evaluate_advisory_record_purge(
    *,
    record: AdvisoryRecordLifecycleState,
    as_of: datetime,
    authorized: bool,
    requested_by: str,
    idempotency_key: str,
) -> AdvisoryRecordPurgeDecision:
    policy = advisory_record_retention_policy(record.record_family)
    reason_code = _purge_reason_code(record=record, as_of=as_of, authorized=authorized)
    return AdvisoryRecordPurgeDecision(
        eligible=reason_code == "PURGE_ELIGIBLE",
        reason_code=reason_code,
        audit_event={
            "event_type": "ADVISORY_RECORD_PURGE_DECISION",
            "record_family": record.record_family,
            "record_ref_hash": _record_ref_hash(record),
            "retention_class": record.retention_class,
            "policy_retention_class": policy.retention_class,
            "policy_owner": policy.owner,
            "purge_policy": policy.purge_policy,
            "requested_by_hash": _subject_hash(requested_by),
            "idempotency_key_hash": _subject_hash(idempotency_key),
            "decision": reason_code,
            "legal_hold": record.legal_hold,
            "dependent_record_count": len(record.dependent_record_refs),
            "tombstone_required": reason_code == "PURGE_ELIGIBLE",
        },
    )


def build_legal_hold_audit_event(
    *,
    record: AdvisoryRecordLifecycleState,
    action: Literal["APPLY_HOLD", "RELEASE_HOLD"],
    actor_id: str,
    reason: str,
    occurred_at: datetime,
) -> dict[str, object]:
    policy = advisory_record_retention_policy(record.record_family)
    return {
        "event_type": "ADVISORY_RECORD_LEGAL_HOLD",
        "record_family": record.record_family,
        "record_ref_hash": _record_ref_hash(record),
        "retention_class": record.retention_class,
        "policy_owner": policy.owner,
        "action": action,
        "actor_hash": _subject_hash(actor_id),
        "reason_hash": _subject_hash(reason),
        "occurred_at": occurred_at.isoformat(),
        "append_only": True,
    }


def _purge_reason_code(
    *,
    record: AdvisoryRecordLifecycleState,
    as_of: datetime,
    authorized: bool,
) -> str:
    if not authorized:
        return "PURGE_NOT_AUTHORIZED"
    if record.tombstoned:
        return "PURGE_ALREADY_TOMBSTONED"
    if record.legal_hold:
        return "PURGE_BLOCKED_BY_LEGAL_HOLD"
    if record.dependent_record_refs:
        return "PURGE_BLOCKED_BY_DEPENDENCIES"
    if record.retention_expires_at is None or record.retention_expires_at > as_of:
        return "PURGE_BLOCKED_BY_RETENTION"
    return "PURGE_ELIGIBLE"


def _record_ref_hash(record: AdvisoryRecordLifecycleState) -> str:
    return cast(
        str,
        hash_canonical_payload(
            {
                "record_family": record.record_family,
                "record_id": record.record_id,
            }
        ),
    )


def _subject_hash(value: str) -> str:
    return cast(str, hash_canonical_payload({"subject": value}))
