from __future__ import annotations

from typing import Any

from src.core.policy_packs.persistence_models import PolicyEvaluationAuditEvent


def conflict_posture_for_workflow(
    *, record: Any, events: list[PolicyEvaluationAuditEvent]
) -> dict[str, Any]:
    reason_codes, blockers = conflict_evidence_from_record(record)
    outcomes = conflict_review_outcomes(events)
    if material_conflict_resolved(outcomes):
        return {
            "status": "SATISFIED",
            "reason_codes": unique(reason_codes),
            "blockers": [],
            "review_outcome": "NO_MATERIAL_CONFLICT_REMAINING",
        }
    blocked = material_conflict_blocks_workflow(reason_codes=reason_codes, blockers=blockers)
    return {
        "status": "BLOCKED" if blocked else "SATISFIED",
        "reason_codes": unique(reason_codes),
        "blockers": unique(blockers) if blocked else [],
        "review_outcome": outcomes[-1] if outcomes else None,
    }


def conflict_evidence_from_record(record: Any) -> tuple[list[str], list[str]]:
    reason_codes: list[str] = []
    blockers: list[str] = []
    for result in conflict_rule_results(record):
        reason_codes.extend(str(item) for item in result.get("reason_codes", []))
        blockers.extend(str(item) for item in result.get("required_actions", []))
    return reason_codes, blockers


def conflict_rule_results(record: Any) -> list[dict[str, Any]]:
    rule_results = record.evaluation_json.get("rule_results", [])
    return [
        result
        for result in rule_results
        if isinstance(result, dict) and "CONFLICT" in str(result.get("rule_id", ""))
    ]


def conflict_review_outcomes(events: list[PolicyEvaluationAuditEvent]) -> list[str]:
    return [
        str(event.reason_json.get("conflict_review_outcome"))
        for event in events
        if event.reason_json.get("conflict_review_outcome")
    ]


def material_conflict_resolved(outcomes: list[str]) -> bool:
    return "NO_MATERIAL_CONFLICT_REMAINING" in outcomes


def material_conflict_blocks_workflow(*, reason_codes: list[str], blockers: list[str]) -> bool:
    return any("MATERIAL_CONFLICT" in code for code in reason_codes) or any(
        blocker in {"SUPERVISORY_CONFLICT_REVIEW", "REVIEW_CONFLICT_OF_INTEREST"}
        for blocker in blockers
    )


def unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = ["conflict_posture_for_workflow"]
