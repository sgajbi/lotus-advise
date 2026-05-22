from __future__ import annotations

from typing import Any

from src.core.common.canonical import hash_canonical_payload
from src.core.proposals.exceptions import ProposalValidationError


def build_reviewed_narrative_report_package(
    *,
    proposal_id: str,
    version_no: int,
    replay_evidence: dict[str, Any],
) -> dict[str, Any]:
    narrative = replay_evidence.get("proposal_narrative")
    if not isinstance(narrative, dict):
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_NOT_FOUND")

    review = replay_evidence.get("proposal_narrative_review")
    if not isinstance(review, dict):
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_REQUIRED")

    review_state = str(review.get("review_state") or "")
    if review_state != "APPROVED_FOR_ADVISOR_USE":
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_NOT_APPROVED")

    narrative_id = str(narrative.get("narrative_id") or "")
    review_id = str(review.get("review_id") or "")
    if not narrative_id or not review_id:
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_INCOMPLETE")

    narrative_status = str(narrative.get("status") or "")
    current_hash = hash_canonical_payload(narrative)
    reviewed_hash = str(review.get("source_narrative_hash") or "")
    if reviewed_hash != current_hash:
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_HASH_MISMATCH")

    guardrail_results = _list_of_dicts(narrative.get("guardrail_results"))
    delivery = replay_evidence.get("delivery") if isinstance(replay_evidence, dict) else None
    execution_boundary = delivery.get("execution") if isinstance(delivery, dict) else None

    return {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "usage": "ADVISOR_REVIEW_AND_REPORT_CONTEXT",
        "proposal_id": proposal_id,
        "proposal_version_no": version_no,
        "narrative_id": narrative_id,
        "narrative_status": narrative_status,
        "generation_mode": narrative.get("generation_mode"),
        "audience": narrative.get("audience"),
        "policy_version": narrative.get("policy_version"),
        "review": {
            "review_id": review_id,
            "review_state": review_state,
            "client_ready_status": review.get("client_ready_status"),
            "reviewed_by": review.get("reviewed_by"),
            "reviewed_at": review.get("reviewed_at"),
            "source_narrative_hash": reviewed_hash,
        },
        "source_lineage": {
            "source_narrative_hash": reviewed_hash,
            "request_hash": replay_evidence.get("request_hash"),
            "artifact_hash": replay_evidence.get("artifact_hash"),
            "simulation_hash": replay_evidence.get("simulation_hash"),
        },
        "sections": _list_of_dicts(narrative.get("sections")),
        "disclosures": _list_of_dicts(narrative.get("disclosures")),
        "guardrail_results": guardrail_results,
        "limitations": _list_of_dicts(narrative.get("limitations")),
        "ai_lineage": narrative.get("ai_lineage"),
        "execution_boundary": execution_boundary,
    }


def summarize_narrative_report_package(package: dict[str, Any] | None) -> dict[str, Any] | None:
    if package is None:
        return None
    review_payload = package.get("review")
    review: dict[str, Any] = review_payload if isinstance(review_payload, dict) else {}
    return {
        "package_status": package.get("package_status"),
        "usage": package.get("usage"),
        "proposal_version_no": package.get("proposal_version_no"),
        "narrative_id": package.get("narrative_id"),
        "review_id": review.get("review_id"),
        "review_state": review.get("review_state"),
        "client_ready_status": review.get("client_ready_status"),
        "source_narrative_hash": review.get("source_narrative_hash"),
    }


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
