from __future__ import annotations

from typing import Any

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_result_builders import (
    rule_blocked,
    rule_pending,
    rule_ready,
    unique_strings,
)
from src.core.proposals.source_readiness_common import list_at

FIELD_TO_SOURCE_SECTION = {
    "private_asset_or_structured_product_flag": "core_product_eligibility_target_market_complexity",
}


def required_source_result(
    *, rule: dict[str, Any], source_posture: dict[str, Any]
) -> PolicyRuleEvaluationResult | None:
    sections: dict[str, dict[str, Any]] = {
        str(section.get("key")): section
        for section in list_at(source_posture, "sections")
        if isinstance(section, dict)
    }
    missing: list[str] = []
    reasons: list[str] = []
    pending = False
    for field in list_at(rule, "required_evidence_fields"):
        field_key = str(field)
        if field_key.startswith(("fee_", "conflict_", "product_document_")):
            continue
        field_key = FIELD_TO_SOURCE_SECTION.get(field_key, field_key)
        if field_key.startswith("policy_source_readiness."):
            if source_posture.get("overall_posture") == "BLOCKED":
                for source_section in sections_with_status(source_posture, "BLOCKED"):
                    missing.extend(
                        str(item) for item in list_at(source_section, "missing_evidence")
                    )
                    reasons.extend(str(item) for item in list_at(source_section, "reason_codes"))
            elif source_posture.get("overall_posture") == "PENDING_REVIEW":
                pending = True
                for source_section in sections_with_status(source_posture, "PENDING_REVIEW"):
                    missing.extend(
                        str(item) for item in list_at(source_section, "missing_evidence")
                    )
                    reasons.extend(str(item) for item in list_at(source_section, "reason_codes"))
            continue
        section: dict[str, Any] | None = sections.get(field_key)
        if section is None:
            missing.append(field_key)
            reasons.append("POLICY_SOURCE_SECTION_MISSING")
            continue
        if section.get("status") == "BLOCKED":
            missing.extend(str(item) for item in list_at(section, "missing_evidence"))
            reasons.extend(str(item) for item in list_at(section, "reason_codes"))
        elif section.get("status") in {"PENDING_REVIEW", "NOT_AVAILABLE"}:
            pending = True
            missing.extend(str(item) for item in list_at(section, "missing_evidence"))
            reasons.extend(str(item) for item in list_at(section, "reason_codes"))
    if missing and not pending:
        return rule_blocked(
            rule,
            outcome="SOURCE_EVIDENCE_BLOCKED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=["RESTORE_SOURCE_OWNER_EVIDENCE"],
        )
    if missing or pending:
        return rule_pending(
            rule,
            outcome="SOURCE_EVIDENCE_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=["REVIEW_SOURCE_OWNER_EVIDENCE"],
        )
    return None


def evaluate_mandate_rule(
    *, rule: dict[str, Any], source_posture: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    mandate_section = section(source_posture, "core_mandate_objectives_restrictions")
    restrictions = list_at(mandate_section, "evidence_refs")
    return rule_ready(
        rule,
        "MANDATE_OBJECTIVES_AND_RESTRICTIONS_READY_FOR_ADVISOR_REVIEW",
        evidence_refs=restrictions,
        source_authority_refs=["lotus-core:core_mandate_objectives_restrictions"],
    )


def section(source_posture: dict[str, Any], key: str) -> dict[str, Any]:
    for source_section in list_at(source_posture, "sections"):
        if isinstance(source_section, dict) and source_section.get("key") == key:
            return source_section
    return {}


def sections_with_status(source_posture: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return [
        source_section
        for source_section in list_at(source_posture, "sections")
        if isinstance(source_section, dict) and source_section.get("status") == status
    ]


__all__ = [
    "evaluate_mandate_rule",
    "required_source_result",
    "section",
    "sections_with_status",
]
