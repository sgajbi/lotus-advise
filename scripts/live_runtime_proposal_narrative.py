from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from src.core.advisory.narrative_models import ProposalNarrativeSection
from src.core.advisory.narrative_policy import evaluate_proposal_narrative_guardrails


@dataclass(frozen=True)
class LiveProposalNarrativeSnapshot:
    proposal_id: str
    version_no: int
    narrative_id: str
    generation_mode: str
    policy_status: str
    persisted_guardrail_statuses: tuple[str, ...]
    read_posture_source: str
    regeneration_persistence_status: str
    review_state: str
    client_ready_status: str
    source_narrative_hash: str
    report_status: str
    report_package_status: str
    replay_review_state: str
    guardrail_failure_status: str
    guardrail_failure_ids: tuple[str, ...]
    ai_assisted_status: str
    ai_fallback_reason: str | None
    latency_ms: float


def summarize_guardrail_statuses(narrative: dict[str, Any]) -> tuple[str, ...]:
    results = narrative.get("guardrail_results")
    if not isinstance(results, list):
        return ()
    statuses: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        guardrail_id = str(item.get("guardrail_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if guardrail_id and status:
            statuses.append(f"{guardrail_id}:{status}")
    return tuple(statuses)


def extract_ai_lineage_status(narrative: dict[str, Any]) -> tuple[str, str | None]:
    ai_lineage = narrative.get("ai_lineage")
    if not isinstance(ai_lineage, dict):
        return "NOT_REQUESTED", None
    fallback_reason = ai_lineage.get("fallback_reason")
    if fallback_reason:
        return "DETERMINISTIC_FALLBACK", str(fallback_reason)
    if ai_lineage.get("workflow_run_id"):
        return "AI_ASSISTED_VALIDATED", None
    return "AI_LINEAGE_PRESENT", None


def validate_guardrail_failure_path() -> tuple[str, tuple[str, ...]]:
    section = ProposalNarrativeSection(
        section_key="EXECUTIVE_SUMMARY",
        title="Executive Summary",
        text="This proposal includes a guaranteed return with no downside risk.",
        source_refs=[],
    )
    results = evaluate_proposal_narrative_guardrails([section])
    failure_ids = tuple(
        str(item.guardrail_id) for item in results if item.status == "FAIL" and item.guardrail_id
    )
    if not failure_ids:
        raise ValueError("Narrative guardrail failure path did not emit a failing result")
    return "LOCAL_POLICY_REPRODUCED", failure_ids


def extract_live_narrative_snapshot(
    *,
    proposal_id: str,
    version_no: int,
    created_version: dict[str, Any],
    read_body: dict[str, Any],
    regeneration_body: dict[str, Any],
    review_body: dict[str, Any],
    replay_body: dict[str, Any],
    report_status: str,
    report_body: dict[str, Any] | None,
    latency_ms: float,
    ai_assisted_status: str | None = None,
    ai_fallback_reason: str | None = None,
) -> LiveProposalNarrativeSnapshot:
    created_narrative = cast(
        dict[str, Any],
        cast(dict[str, Any], created_version["artifact"])["proposal_narrative"],
    )
    read_narrative = cast(dict[str, Any], read_body["proposal_narrative"])
    review_record = cast(dict[str, Any], review_body["narrative_review"])
    replay_review = cast(
        dict[str, Any],
        cast(dict[str, Any], replay_body["evidence"])["proposal_narrative_review"],
    )
    regeneration_posture = cast(dict[str, Any], regeneration_body["regeneration_posture"])
    read_posture = cast(dict[str, Any], read_body["read_posture"])
    package = None
    if isinstance(report_body, dict):
        explanation = cast(dict[str, Any], report_body["explanation"])
        package = cast(
            dict[str, Any] | None,
            explanation.get("proposal_narrative_package"),
        )
    guardrail_failure_status, guardrail_failure_ids = validate_guardrail_failure_path()
    default_ai_status, default_ai_fallback_reason = extract_ai_lineage_status(created_narrative)

    return LiveProposalNarrativeSnapshot(
        proposal_id=proposal_id,
        version_no=version_no,
        narrative_id=str(created_narrative["narrative_id"]),
        generation_mode=str(created_narrative["generation_mode"]),
        policy_status=str(cast(dict[str, Any], created_narrative["narrative_policy"])["status"]),
        persisted_guardrail_statuses=summarize_guardrail_statuses(read_narrative),
        read_posture_source=str(read_posture["source"]),
        regeneration_persistence_status=str(regeneration_posture["persistence_status"]),
        review_state=str(review_record["review_state"]),
        client_ready_status=str(review_record["client_ready_status"]),
        source_narrative_hash=str(review_record["source_narrative_hash"]),
        report_status=report_status,
        report_package_status=(
            str(package["package_status"]) if isinstance(package, dict) else "UNAVAILABLE"
        ),
        replay_review_state=str(replay_review["review_state"]),
        guardrail_failure_status=guardrail_failure_status,
        guardrail_failure_ids=guardrail_failure_ids,
        ai_assisted_status=ai_assisted_status or default_ai_status,
        ai_fallback_reason=ai_fallback_reason or default_ai_fallback_reason,
        latency_ms=latency_ms,
    )
