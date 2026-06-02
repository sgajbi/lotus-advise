from __future__ import annotations

from typing import Any

from src.core.proposals.models import ProposalMemoReportPackageRequest
from src.core.proposals.persistence_models import ProposalMemoRecord


def build_report_memo_package(
    *,
    memo: ProposalMemoRecord,
    payload: ProposalMemoReportPackageRequest,
    review_posture: dict[str, Any],
) -> dict[str, Any]:
    memo_json = dict(memo.memo_json)
    return {
        "package_status": "INCLUDED_ADVISOR_PROPOSAL_MEMO",
        "usage": "REPORT_REQUEST_APPROVED_ADVISOR_MEMO",
        "memo_id": memo.memo_id,
        "memo_version": memo.memo_version,
        "memo_status": memo.memo_status,
        "proposal_id": memo.proposal_id,
        "proposal_version_no": memo.proposal_version_no,
        "proposal_version_id": memo.proposal_version_id,
        "artifact_id": memo.artifact_id,
        "memo_hash": memo.memo_hash,
        "source_input_hash": memo.source_input_hash,
        "review": {
            "review_event_id": review_posture.get("event_id"),
            "review_action": review_posture.get("review_action"),
            "reviewed_by": review_posture.get("actor_id"),
            "reviewed_at": review_posture.get("occurred_at"),
            "review_reason": review_posture.get("review_reason"),
        },
        "projection": dict(memo.projection_json),
        "sections": memo_json.get("sections", []),
        "source_authority_manifest": memo_json.get("source_authority_manifest", {}),
        "supportability": memo_json.get("supportability", {}),
        "requested_output_formats": payload.requested_output_formats,
        "client_ready_publication": "BLOCKED",
        "report_request_reason": payload.reason,
    }


def build_memo_ai_evidence(
    *,
    memo: ProposalMemoRecord,
    review_posture: dict[str, Any],
) -> dict[str, Any]:
    memo_json = dict(memo.memo_json)
    return {
        "memo_id": memo.memo_id,
        "memo_version": memo.memo_version,
        "memo_status": memo.memo_status,
        "memo_hash": memo.memo_hash,
        "source_input_hash": memo.source_input_hash,
        "proposal_id": memo.proposal_id,
        "proposal_version_no": memo.proposal_version_no,
        "proposal_version_id": memo.proposal_version_id,
        "artifact_id": memo.artifact_id,
        "review": {
            "review_event_id": review_posture.get("event_id"),
            "review_action": review_posture.get("review_action"),
            "reviewed_by": review_posture.get("actor_id"),
            "reviewed_at": review_posture.get("occurred_at"),
        },
        "projection": dict(memo.projection_json),
        "sections": memo_json.get("sections", []),
        "source_refs": memo_source_refs(memo_json),
        "supportability": memo_json.get("supportability", {}),
        "client_ready_publication": "BLOCKED",
    }


def memo_source_refs(memo_json: dict[str, Any]) -> list[str]:
    manifest = memo_json.get("source_authority_manifest")
    if not isinstance(manifest, dict):
        return []
    refs = manifest.get("source_refs")
    if not isinstance(refs, list):
        return []
    return [item for item in refs if isinstance(item, str)]
