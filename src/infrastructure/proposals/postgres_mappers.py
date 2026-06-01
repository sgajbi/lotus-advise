from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, cast

from src.core.proposals.models import (
    ProposalApprovalRecordData,
    ProposalAsyncOperationRecord,
    ProposalMemoEventRecord,
    ProposalMemoRecord,
    ProposalRecord,
    ProposalVersionRecord,
    ProposalWorkflowEventRecord,
)


def optional_iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


def optional_json(value: Optional[dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json_dump(value)


def json_dump(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def json_dump_list(value: list[dict[str, Any]]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def json_load_list(value: str) -> list[dict[str, Any]]:
    loaded = json.loads(value)
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def optional_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def optional_load_json(value: Optional[str]) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    return cast(dict[str, Any], json.loads(value))


def to_operation(row: Any) -> Optional[ProposalAsyncOperationRecord]:
    if row is None:
        return None
    return ProposalAsyncOperationRecord(
        operation_id=row["operation_id"],
        operation_type=row["operation_type"],
        status=row["status"],
        correlation_id=row["correlation_id"],
        idempotency_key=row["idempotency_key"],
        proposal_id=row["proposal_id"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        payload_json=optional_load_json(row["payload_json"]) or {},
        attempt_count=int(row["attempt_count"]),
        max_attempts=int(row["max_attempts"]),
        started_at=optional_datetime(row["started_at"]),
        lease_expires_at=optional_datetime(row["lease_expires_at"]),
        finished_at=optional_datetime(row["finished_at"]),
        result_json=optional_load_json(row["result_json"]),
        error_json=optional_load_json(row["error_json"]),
    )


def to_proposal(row: Any) -> Optional[ProposalRecord]:
    if row is None:
        return None
    return ProposalRecord(
        proposal_id=row["proposal_id"],
        portfolio_id=row["portfolio_id"],
        mandate_id=row["mandate_id"],
        jurisdiction=row["jurisdiction"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_event_at=datetime.fromisoformat(row["last_event_at"]),
        current_state=row["current_state"],
        current_version_no=int(row["current_version_no"]),
        title=row["title"],
        advisor_notes=row["advisor_notes"],
        lifecycle_origin=row["lifecycle_origin"],
        source_workspace_id=row["source_workspace_id"],
    )


def to_version(row: Any) -> Optional[ProposalVersionRecord]:
    if row is None:
        return None
    return ProposalVersionRecord(
        proposal_version_id=row["proposal_version_id"],
        proposal_id=row["proposal_id"],
        version_no=int(row["version_no"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        request_hash=row["request_hash"],
        artifact_hash=row["artifact_hash"],
        simulation_hash=row["simulation_hash"],
        status_at_creation=row["status_at_creation"],
        proposal_result_json=json.loads(row["proposal_result_json"]),
        artifact_json=json.loads(row["artifact_json"]),
        evidence_bundle_json=json.loads(row["evidence_bundle_json"]),
        gate_decision_json=optional_load_json(row["gate_decision_json"]),
    )


def to_memo(row: Any) -> Optional[ProposalMemoRecord]:
    if row is None:
        return None
    return ProposalMemoRecord(
        memo_id=row["memo_id"],
        proposal_id=row["proposal_id"],
        proposal_version_no=int(row["proposal_version_no"]),
        proposal_version_id=row["proposal_version_id"],
        artifact_id=row["artifact_id"],
        memo_version=row["memo_version"],
        memo_status=row["memo_status"],
        lifecycle_status=row["lifecycle_status"],
        created_by=row["created_by"],
        created_at=datetime.fromisoformat(row["created_at"]),
        source_input_hash=row["source_input_hash"],
        memo_hash=row["memo_hash"],
        memo_json=optional_load_json(row["memo_json"]) or {},
        projection_json=optional_load_json(row["projection_json"]) or {},
        review_events_json=json_load_list(row["review_events_json"]),
        report_package_events_json=json_load_list(row["report_package_events_json"]),
        archive_refs_json=json_load_list(row["archive_refs_json"]),
        ai_refs_json=json_load_list(row["ai_refs_json"]),
        replay_metadata_json=optional_load_json(row["replay_metadata_json"]) or {},
    )


def to_memo_event(row: Any) -> ProposalMemoEventRecord:
    return ProposalMemoEventRecord(
        event_id=row["event_id"],
        memo_id=row["memo_id"],
        proposal_id=row["proposal_id"],
        proposal_version_no=int(row["proposal_version_no"]),
        event_type=row["event_type"],
        actor_id=row["actor_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        reason_json=optional_load_json(row["reason_json"]) or {},
    )


def to_event(row: Any) -> ProposalWorkflowEventRecord:
    return ProposalWorkflowEventRecord(
        event_id=row["event_id"],
        proposal_id=row["proposal_id"],
        event_type=row["event_type"],
        from_state=row["from_state"],
        to_state=row["to_state"],
        actor_id=row["actor_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        reason_json=json.loads(row["reason_json"]),
        related_version_no=row["related_version_no"],
    )


def to_approval(row: Any) -> ProposalApprovalRecordData:
    return ProposalApprovalRecordData(
        approval_id=row["approval_id"],
        proposal_id=row["proposal_id"],
        approval_type=row["approval_type"],
        approved=bool(row["approved"]),
        actor_id=row["actor_id"],
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        details_json=json.loads(row["details_json"]),
        related_version_no=row["related_version_no"],
    )


__all__ = [
    "json_dump",
    "json_dump_list",
    "json_load_list",
    "optional_datetime",
    "optional_iso",
    "optional_json",
    "optional_load_json",
    "to_approval",
    "to_event",
    "to_memo",
    "to_memo_event",
    "to_operation",
    "to_proposal",
    "to_version",
]
