from __future__ import annotations

from typing import Any

from src.core.policy_packs.supportability import REFERENCE_POLICY_PACK_POSTURE

REFERENCE_POSTURE = REFERENCE_POLICY_PACK_POSTURE

REQUIRED_DEFINITION_FIELDS = (
    "policy_pack_id",
    "policy_version",
    "policy_family",
    "applicability",
    "source_requirements",
    "rules",
    "sample_fixture_refs",
    "schema_version",
)


def validate_catalog_definition(definition: dict[str, Any]) -> list[str]:
    diagnostics = [
        *required_field_diagnostics(definition),
        *reference_posture_diagnostics(definition),
        *rule_collection_diagnostics(definition),
    ]
    return diagnostics


def required_field_diagnostics(definition: dict[str, Any]) -> list[str]:
    return [
        f"{key.upper()}_REQUIRED" for key in REQUIRED_DEFINITION_FIELDS if not definition.get(key)
    ]


def reference_posture_diagnostics(definition: dict[str, Any]) -> list[str]:
    if definition.get("reference_posture") == REFERENCE_POSTURE:
        return []
    return ["REFERENCE_POSTURE_NOT_DECLARED"]


def rule_collection_diagnostics(definition: dict[str, Any]) -> list[str]:
    rules = definition.get("rules")
    if not isinstance(rules, list):
        return ["RULES_MUST_BE_LIST"]
    diagnostics: list[str] = []
    for rule in rules:
        diagnostics.extend(rule_diagnostics(rule))
    return diagnostics


def rule_diagnostics(rule: Any) -> list[str]:
    if not isinstance(rule, dict):
        return ["RULE_MUST_BE_OBJECT"]
    rule_id = rule_identifier(rule)
    diagnostics = [
        *rule_identifier_diagnostics(rule_id),
        *required_evidence_field_diagnostics(rule=rule, rule_id=rule_id),
        *missing_evidence_wording_diagnostics(rule=rule, rule_id=rule_id),
    ]
    return diagnostics


def rule_identifier(rule: dict[str, Any]) -> str:
    return str(rule.get("rule_id") or "")


def rule_identifier_diagnostics(rule_id: str) -> list[str]:
    if rule_id and rule_id.upper() == rule_id and "-" not in rule_id:
        return []
    return ["RULE_ID_NOT_UPPER_SNAKE_CASE"]


def required_evidence_field_diagnostics(*, rule: dict[str, Any], rule_id: str) -> list[str]:
    if rule.get("required_evidence_fields"):
        return []
    return [f"{rule_id or 'RULE'}_REQUIRED_EVIDENCE_FIELDS_REQUIRED"]


def missing_evidence_wording_diagnostics(*, rule: dict[str, Any], rule_id: str) -> list[str]:
    if "positive_wording_when_missing_evidence" not in rule:
        return []
    return [f"{rule_id or 'RULE'}_FORBIDDEN_POSITIVE_MISSING_EVIDENCE_WORDING"]


__all__ = ["validate_catalog_definition"]
