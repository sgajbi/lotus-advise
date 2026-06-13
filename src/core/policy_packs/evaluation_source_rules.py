from __future__ import annotations

from dataclasses import dataclass
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
_ADVISORY_REVIEW_ONLY_FIELD_PREFIXES = ("fee_", "conflict_", "product_document_")
_POLICY_SOURCE_READINESS_PREFIX = "policy_source_readiness."


@dataclass
class _SourceEvidenceCollection:
    missing: list[str]
    reasons: list[str]
    pending: bool = False

    def extend_from_section(self, source_section: dict[str, Any]) -> None:
        self.missing.extend(str(item) for item in list_at(source_section, "missing_evidence"))
        self.reasons.extend(str(item) for item in list_at(source_section, "reason_codes"))


def required_source_result(
    *, rule: dict[str, Any], source_posture: dict[str, Any]
) -> PolicyRuleEvaluationResult | None:
    sections = sections_by_key(source_posture)
    collection = _SourceEvidenceCollection(missing=[], reasons=[])
    for field_key in _source_evidence_fields(rule):
        if field_key.startswith(_POLICY_SOURCE_READINESS_PREFIX):
            _collect_policy_source_readiness_evidence(source_posture, collection)
            continue
        _collect_section_source_evidence(field_key, sections, collection)
    return _source_evidence_result(rule=rule, collection=collection)


def sections_by_key(source_posture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(section.get("key")): section
        for section in list_at(source_posture, "sections")
        if isinstance(section, dict)
    }


def _source_evidence_fields(rule: dict[str, Any]) -> list[str]:
    return [
        FIELD_TO_SOURCE_SECTION.get(field_key, field_key)
        for field_key in _required_evidence_field_keys(rule)
        if not _is_advisory_review_only_field(field_key)
    ]


def _required_evidence_field_keys(rule: dict[str, Any]) -> list[str]:
    return [str(field) for field in list_at(rule, "required_evidence_fields")]


def _is_advisory_review_only_field(field_key: str) -> bool:
    return field_key.startswith(_ADVISORY_REVIEW_ONLY_FIELD_PREFIXES)


def _source_evidence_result(
    *,
    rule: dict[str, Any],
    collection: _SourceEvidenceCollection,
) -> PolicyRuleEvaluationResult | None:
    if collection.missing and not collection.pending:
        return rule_blocked(
            rule,
            outcome="SOURCE_EVIDENCE_BLOCKED",
            missing_evidence=unique_strings(collection.missing),
            reason_codes=unique_strings(collection.reasons),
            required_actions=["RESTORE_SOURCE_OWNER_EVIDENCE"],
        )
    if collection.missing or collection.pending:
        return rule_pending(
            rule,
            outcome="SOURCE_EVIDENCE_REVIEW_REQUIRED",
            missing_evidence=unique_strings(collection.missing),
            reason_codes=unique_strings(collection.reasons),
            required_actions=["REVIEW_SOURCE_OWNER_EVIDENCE"],
        )
    return None


def _collect_policy_source_readiness_evidence(
    source_posture: dict[str, Any], collection: _SourceEvidenceCollection
) -> None:
    overall_posture = source_posture.get("overall_posture")
    if overall_posture == "BLOCKED":
        for source_section in sections_with_status(source_posture, "BLOCKED"):
            collection.extend_from_section(source_section)
    elif overall_posture == "PENDING_REVIEW":
        collection.pending = True
        for source_section in sections_with_status(source_posture, "PENDING_REVIEW"):
            collection.extend_from_section(source_section)


def _collect_section_source_evidence(
    field_key: str,
    sections: dict[str, dict[str, Any]],
    collection: _SourceEvidenceCollection,
) -> None:
    source_section = sections.get(field_key)
    if source_section is None:
        collection.missing.append(field_key)
        collection.reasons.append("POLICY_SOURCE_SECTION_MISSING")
        return
    if source_section.get("status") == "BLOCKED":
        collection.extend_from_section(source_section)
    elif source_section.get("status") in {"PENDING_REVIEW", "NOT_AVAILABLE"}:
        collection.pending = True
        collection.extend_from_section(source_section)


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
