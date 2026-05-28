from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True)
class LivePolicyEvaluationSnapshot:
    proposal_id: str
    proposal_version_id: str
    evaluation_id: str
    policy_pack_id: str
    policy_version: str
    evaluation_status: str
    evaluation_hash: str
    source_evidence_hash: str
    policy_content_hash: str
    material_rule_count: int
    pending_rule_count: int
    approval_dependency_count: int
    disclosure_requirement_count: int
    consent_requirement_count: int
    source_ref_count: int
    source_gap_count: int
    review_queue_status: str
    workflow_sign_off_status: str
    workflow_client_ready_publication: str
    workflow_open_requirement_count: int
    sign_off_decision_status: str
    report_status: str
    report_package_status: str
    requested_output_formats: tuple[str, ...]
    render_ref_status: str
    archive_ref_status: str
    archive_retention_posture: str
    archive_legal_hold_posture: str
    archive_access_audit_ref_status: str
    ai_status: str
    ai_authoritative_for_policy_status: bool
    ai_human_review_required: bool
    ai_raw_source_evidence_included: bool
    lineage_complete: bool
    lineage_event_count: int
    replay_evaluation_hash_matches: bool
    replay_source_evidence_hash_matches: bool
    stale_hash_block_status: str
    client_ready_document_block_status: str
    forbidden_ai_action_block_status: str
    report_degraded_reason: str | None
    latency_ms: float


def extract_live_policy_evaluation_snapshot(
    *,
    created_body: dict[str, Any],
    read_body: dict[str, Any],
    queue_body: dict[str, Any],
    workflow_body: dict[str, Any],
    sign_off_body: dict[str, Any],
    report_status: str,
    report_body: dict[str, Any] | None,
    ai_body: dict[str, Any],
    lineage_body: dict[str, Any],
    replay_body: dict[str, Any],
    stale_hash_block_status: str,
    client_ready_document_block_status: str,
    forbidden_ai_action_block_status: str,
    report_degraded_reason: str | None,
    latency_ms: float,
) -> LivePolicyEvaluationSnapshot:
    record = cast(dict[str, Any], created_body["record"])
    read_record = read_body
    evaluation_json = cast(dict[str, Any], read_record["evaluation_json"])
    rule_results = cast(list[dict[str, Any]], evaluation_json.get("rule_results", []))
    workflow = cast(dict[str, Any], sign_off_body["workflow"])
    ai_evidence = cast(dict[str, Any], ai_body["policy_evidence"])
    redaction_profile = cast(dict[str, Any], ai_evidence["redaction_profile"])
    hash_comparison = cast(dict[str, Any], replay_body["hash_comparison"])

    report_package_status = "UNAVAILABLE"
    requested_output_formats: tuple[str, ...] = ()
    render_ref_status = "UNAVAILABLE"
    archive_ref_status = "UNAVAILABLE"
    archive_retention_posture = "NOT_RETURNED"
    archive_legal_hold_posture = "NOT_RETURNED"
    archive_access_audit_ref_status = "NOT_RETURNED"
    if report_body is not None:
        report_event = cast(dict[str, Any], report_body["report_package_event"])
        reason = _event_reason(report_event)
        report_package_status = str(reason.get("report_package_status", "UNKNOWN"))
        requested_output_formats = tuple(
            str(item) for item in cast(list[Any], reason.get("requested_output_formats", []))
        )
        archive = reason.get("archive")
        render_ref_status = _ref_status(reason.get("render"), key="render_job_id")
        archive_ref_status = _ref_status(archive, key="document_id")
        archive_retention_posture = _archive_posture(archive, key="retention_posture")
        archive_legal_hold_posture = _archive_posture(archive, key="legal_hold_posture")
        archive_access_audit_ref_status = _ref_status(archive, key="access_audit_ref")

    return LivePolicyEvaluationSnapshot(
        proposal_id=str(record["proposal_id"]),
        proposal_version_id=str(record["proposal_version_id"]),
        evaluation_id=str(record["evaluation_id"]),
        policy_pack_id=str(record["policy_pack_id"]),
        policy_version=str(record["policy_version"]),
        evaluation_status=str(record["evaluation_status"]),
        evaluation_hash=str(record["evaluation_hash"]),
        source_evidence_hash=str(record["source_evidence_hash"]),
        policy_content_hash=str(record["policy_content_hash"]),
        material_rule_count=len(rule_results),
        pending_rule_count=sum(
            1 for item in rule_results if item.get("status") == "PENDING_REVIEW"
        ),
        approval_dependency_count=len(cast(list[Any], record["approval_dependencies"])),
        disclosure_requirement_count=len(cast(list[Any], record["disclosure_requirements"])),
        consent_requirement_count=len(cast(list[Any], record["consent_requirements"])),
        source_ref_count=len(cast(list[Any], record["source_refs"])),
        source_gap_count=len(cast(list[Any], record["source_gaps"])),
        review_queue_status=_review_queue_status(
            queue_body=queue_body, evaluation_id=record["evaluation_id"]
        ),
        workflow_sign_off_status=str(workflow_body["sign_off_status"]),
        workflow_client_ready_publication=str(workflow_body["client_ready_publication"]),
        workflow_open_requirement_count=int(
            cast(dict[str, Any], workflow_body["sla_posture"])["open_requirement_count"]
        ),
        sign_off_decision_status=str(workflow["sign_off_status"]),
        report_status=report_status,
        report_package_status=report_package_status,
        requested_output_formats=requested_output_formats,
        render_ref_status=render_ref_status,
        archive_ref_status=archive_ref_status,
        archive_retention_posture=archive_retention_posture,
        archive_legal_hold_posture=archive_legal_hold_posture,
        archive_access_audit_ref_status=archive_access_audit_ref_status,
        ai_status=str(ai_evidence["status"]),
        ai_authoritative_for_policy_status=bool(ai_evidence["authoritative_for_policy_status"]),
        ai_human_review_required=bool(ai_evidence["human_review_required"]),
        ai_raw_source_evidence_included=bool(redaction_profile["raw_source_evidence_included"]),
        lineage_complete=_lineage_complete(lineage_body),
        lineage_event_count=len(cast(list[Any], lineage_body["audit_events"])),
        replay_evaluation_hash_matches=bool(hash_comparison["evaluation_hash_matches"]),
        replay_source_evidence_hash_matches=bool(hash_comparison["source_evidence_hash_matches"]),
        stale_hash_block_status=stale_hash_block_status,
        client_ready_document_block_status=client_ready_document_block_status,
        forbidden_ai_action_block_status=forbidden_ai_action_block_status,
        report_degraded_reason=report_degraded_reason,
        latency_ms=latency_ms,
    )


def _ref_status(value: Any, *, key: str) -> str:
    if isinstance(value, dict) and value.get(key):
        return "RECORDED"
    return "NOT_RETURNED"


def _archive_posture(value: Any, *, key: str) -> str:
    if isinstance(value, dict) and value.get(key):
        return str(value[key])
    return "NOT_RETURNED"


def _event_reason(event: dict[str, Any]) -> dict[str, Any]:
    reason = event.get("reason_json", event.get("reason", {}))
    if isinstance(reason, dict):
        return reason
    return {}


def _lineage_complete(lineage_body: dict[str, Any]) -> bool:
    return bool(
        lineage_body.get("evaluation_hash")
        and lineage_body.get("source_evidence_hash")
        and lineage_body.get("policy_content_hash")
        and lineage_body.get("rule_result_hashes")
        and lineage_body.get("source_refs")
        and lineage_body.get("audit_events")
        and cast(dict[str, Any], lineage_body.get("lineage_posture", {})).get(
            "client_ready_publication"
        )
        == "BLOCKED"
    )


def _review_queue_status(*, queue_body: dict[str, Any], evaluation_id: Any) -> str:
    for item in cast(list[dict[str, Any]], queue_body.get("items", [])):
        if item.get("evaluation_id") == evaluation_id:
            return str(item.get("evaluation_status", "UNKNOWN"))
    return str(
        cast(dict[str, Any], queue_body.get("queue_posture", {})).get("default_filter", "UNKNOWN")
    )
