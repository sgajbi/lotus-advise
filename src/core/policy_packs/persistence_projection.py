from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.policy_packs.persistence_models import (
    PolicyEvaluationAuditEvent,
    PolicyEvaluationRecord,
)
from src.core.policy_packs.projection_models import PolicyEvaluationLineageResponse
from src.core.policy_packs.supportability import policy_runtime_supportability


def attach_policy_evaluation_event(
    *, record: PolicyEvaluationRecord, event: PolicyEvaluationAuditEvent
) -> None:
    payload = event.model_dump(mode="json")
    if event.event_type == "POLICY_EVALUATION_REVIEW_RECORDED":
        record.review_events_json.append(payload)
    elif event.event_type == "POLICY_EVALUATION_SIGN_OFF_RECORDED":
        record.sign_off_events_json.append(payload)
    elif event.event_type == "POLICY_EVALUATION_REPORT_ARCHIVE_RECORDED":
        record.report_archive_refs_json.append(payload)


def build_policy_evaluation_lineage_response(
    *,
    record: PolicyEvaluationRecord,
    audit_events: list[PolicyEvaluationAuditEvent],
) -> PolicyEvaluationLineageResponse:
    return PolicyEvaluationLineageResponse(
        evaluation_id=record.evaluation_id,
        proposal_id=record.proposal_id,
        proposal_version_id=record.proposal_version_id,
        policy_pack_id=record.policy_pack_id,
        policy_version=record.policy_version,
        policy_content_hash=record.policy_content_hash,
        source_evidence_hash=record.source_evidence_hash,
        evaluation_hash=record.evaluation_hash,
        rule_result_hashes=dict(record.rule_result_hashes),
        source_refs=list(record.source_refs),
        source_gaps=list(record.source_gaps),
        audit_events=[deepcopy(event) for event in audit_events],
        lineage_posture=policy_evaluation_api_posture(),
    )


def policy_evaluation_api_posture() -> dict[str, Any]:
    return dict(policy_runtime_supportability())
