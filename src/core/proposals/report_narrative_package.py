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
    narrative = _required_mapping(
        replay_evidence.get("proposal_narrative"),
        missing_code="PROPOSAL_REPORT_NARRATIVE_NOT_FOUND",
    )
    review = _required_mapping(
        replay_evidence.get("proposal_narrative_review"),
        missing_code="PROPOSAL_REPORT_NARRATIVE_REVIEW_REQUIRED",
    )
    review_state = _approved_review_state(review)
    narrative_id = _required_text(
        narrative.get("narrative_id"),
        missing_code="PROPOSAL_REPORT_NARRATIVE_REVIEW_INCOMPLETE",
    )
    review_id = _required_text(
        review.get("review_id"),
        missing_code="PROPOSAL_REPORT_NARRATIVE_REVIEW_INCOMPLETE",
    )
    reviewed_hash = _validated_review_hash(narrative=narrative, review=review)
    return {
        "package_status": "INCLUDED_REVIEWED_NARRATIVE",
        "usage": "ADVISOR_REVIEW_AND_REPORT_CONTEXT",
        "proposal_id": proposal_id,
        "proposal_version_no": version_no,
        "narrative_id": narrative_id,
        "narrative_status": str(narrative.get("status") or ""),
        "generation_mode": narrative.get("generation_mode"),
        "audience": narrative.get("audience"),
        "policy_version": narrative.get("policy_version"),
        "review": _review_payload(
            review=review,
            review_id=review_id,
            review_state=review_state,
            reviewed_hash=reviewed_hash,
        ),
        "source_lineage": _source_lineage(
            replay_evidence=replay_evidence,
            reviewed_hash=reviewed_hash,
        ),
        "sections": _narrative_sections_for_report(narrative.get("sections")),
        "disclosures": _list_of_dicts(narrative.get("disclosures")),
        "guardrail_results": _list_of_dicts(narrative.get("guardrail_results")),
        "limitations": _list_of_dicts(narrative.get("limitations")),
        "ai_lineage": narrative.get("ai_lineage"),
        "execution_boundary": _execution_boundary(replay_evidence),
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


def _required_mapping(value: Any, *, missing_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProposalValidationError(missing_code)
    return value


def _required_text(value: Any, *, missing_code: str) -> str:
    text = str(value or "")
    if not text:
        raise ProposalValidationError(missing_code)
    return text


def _approved_review_state(review: dict[str, Any]) -> str:
    review_state = str(review.get("review_state") or "")
    if review_state != "APPROVED_FOR_ADVISOR_USE":
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_NOT_APPROVED")
    return review_state


def _validated_review_hash(*, narrative: dict[str, Any], review: dict[str, Any]) -> str:
    reviewed_hash = str(review.get("source_narrative_hash") or "")
    if reviewed_hash != hash_canonical_payload(narrative):
        raise ProposalValidationError("PROPOSAL_REPORT_NARRATIVE_REVIEW_HASH_MISMATCH")
    return reviewed_hash


def _review_payload(
    *,
    review: dict[str, Any],
    review_id: str,
    review_state: str,
    reviewed_hash: str,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "review_state": review_state,
        "client_ready_status": review.get("client_ready_status"),
        "reviewed_by": review.get("reviewed_by"),
        "reviewed_at": review.get("reviewed_at"),
        "source_narrative_hash": reviewed_hash,
    }


def _source_lineage(*, replay_evidence: dict[str, Any], reviewed_hash: str) -> dict[str, Any]:
    return {
        "source_narrative_hash": reviewed_hash,
        "request_hash": replay_evidence.get("request_hash"),
        "artifact_hash": replay_evidence.get("artifact_hash"),
        "simulation_hash": replay_evidence.get("simulation_hash"),
    }


def _execution_boundary(replay_evidence: dict[str, Any]) -> Any:
    delivery = replay_evidence.get("delivery")
    return delivery.get("execution") if isinstance(delivery, dict) else None


def _narrative_sections_for_report(value: Any) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for item in _list_of_dicts(value):
        section_id = str(item.get("section_id") or item.get("section_key") or "").strip()
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or item.get("text") or "").strip()
        if not section_id or not title or not body:
            continue
        section = dict(item)
        section["section_id"] = section_id
        section["title"] = title
        section["body"] = body
        section.pop("section_key", None)
        section.pop("text", None)
        sections.append(section)
    return sections
