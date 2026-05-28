from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast


@dataclass(frozen=True)
class LiveProposalMemoSnapshot:
    proposal_id: str
    version_no: int
    memo_id: str
    memo_status: str
    lifecycle_status: str
    memo_hash: str
    source_input_hash: str
    projection_client_ready_publication: str
    projection_audience: str
    projected_section_count: int
    review_action: str
    review_client_ready_publication: str
    report_status: str
    report_package_status: str
    requested_output_formats: tuple[str, ...]
    render_ref_status: str
    archive_ref_status: str
    archive_retention_posture: str
    archive_legal_hold_posture: str
    archive_access_audit_ref_status: str
    ai_status: str
    ai_authoritative_for_memo_status: bool
    ai_review_required: bool
    lineage_complete: bool
    lineage_memo_count: int
    replay_memo_hash: str
    replay_source_input_hash: str
    replay_client_ready_publication: str
    stale_hash_block_status: str
    client_ready_release_block_status: str
    client_ready_document_block_status: str
    report_degraded_reason: str | None
    latency_ms: float


def extract_live_memo_snapshot(
    *,
    proposal_id: str,
    version_no: int,
    memo_body: dict[str, Any],
    projection_body: dict[str, Any],
    review_body: dict[str, Any],
    report_status: str,
    report_body: dict[str, Any] | None,
    ai_body: dict[str, Any],
    lineage_body: dict[str, Any],
    replay_body: dict[str, Any],
    stale_hash_block_status: str,
    client_ready_release_block_status: str,
    client_ready_document_block_status: str,
    report_degraded_reason: str | None,
    latency_ms: float,
) -> LiveProposalMemoSnapshot:
    memo = cast(dict[str, Any], review_body["memo"])
    projection_posture = cast(dict[str, Any], projection_body["projection_posture"])
    review_event = cast(dict[str, Any], review_body["review_event"])
    review_reason = cast(dict[str, Any], review_event["reason"])
    ai_commentary = cast(dict[str, Any], ai_body["commentary"])
    ai_event = cast(dict[str, Any], ai_body["ai_event"])
    ai_reason = cast(dict[str, Any], ai_event["reason"])
    replay_hashes = cast(dict[str, Any], replay_body["hashes"])
    replay_explanation = cast(dict[str, Any], replay_body["explanation"])
    report_package_status = "UNAVAILABLE"
    requested_output_formats: tuple[str, ...] = ()
    render_ref_status = "UNAVAILABLE"
    archive_ref_status = "UNAVAILABLE"
    archive_retention_posture = "NOT_RETURNED"
    archive_legal_hold_posture = "NOT_RETURNED"
    archive_access_audit_ref_status = "NOT_RETURNED"
    if report_body is not None:
        report_event = cast(dict[str, Any], report_body["report_package_event"])
        report_reason = cast(dict[str, Any], report_event["reason"])
        report_package_status = str(report_reason.get("report_package_status", "UNKNOWN"))
        requested_output_formats = tuple(
            str(item) for item in cast(list[Any], report_reason.get("requested_output_formats", []))
        )
        archive = report_reason.get("archive")
        render_ref_status = _ref_status(report_reason.get("render"), key="render_job_id")
        archive_ref_status = _ref_status(archive, key="document_id")
        archive_retention_posture = _archive_posture(archive, key="retention_posture")
        archive_legal_hold_posture = _archive_posture(archive, key="legal_hold_posture")
        archive_access_audit_ref_status = _ref_status(archive, key="access_audit_ref")

    return LiveProposalMemoSnapshot(
        proposal_id=proposal_id,
        version_no=version_no,
        memo_id=str(memo_body["memo_id"]),
        memo_status=str(memo["memo_status"]),
        lifecycle_status=str(memo["lifecycle_status"]),
        memo_hash=str(memo["memo_hash"]),
        source_input_hash=str(memo["source_input_hash"]),
        projection_client_ready_publication=str(projection_posture["client_ready_publication"]),
        projection_audience=str(projection_body["audience"]),
        projected_section_count=len(cast(list[Any], projection_body["sections"])),
        review_action=str(review_reason["review_action"]),
        review_client_ready_publication=str(review_reason["client_ready_publication"]),
        report_status=report_status,
        report_package_status=report_package_status,
        requested_output_formats=requested_output_formats,
        render_ref_status=render_ref_status,
        archive_ref_status=archive_ref_status,
        archive_retention_posture=archive_retention_posture,
        archive_legal_hold_posture=archive_legal_hold_posture,
        archive_access_audit_ref_status=archive_access_audit_ref_status,
        ai_status=str(ai_reason["ai_status"]),
        ai_authoritative_for_memo_status=bool(ai_commentary["authoritative_for_memo_status"]),
        ai_review_required=bool(ai_commentary["review_required"]),
        lineage_complete=bool(lineage_body["lineage_complete"]),
        lineage_memo_count=int(lineage_body["memo_count"]),
        replay_memo_hash=str(replay_hashes["memo_hash"]),
        replay_source_input_hash=str(replay_hashes["source_input_hash"]),
        replay_client_ready_publication=str(replay_explanation["client_ready_publication"]),
        stale_hash_block_status=stale_hash_block_status,
        client_ready_release_block_status=client_ready_release_block_status,
        client_ready_document_block_status=client_ready_document_block_status,
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
