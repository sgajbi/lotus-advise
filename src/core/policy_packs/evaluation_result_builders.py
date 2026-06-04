from __future__ import annotations

from typing import Any

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.proposals.source_readiness_common import list_at


def rule_ready(
    rule: dict[str, Any],
    outcome: str,
    *,
    evidence_refs: list[str] | None = None,
    source_authority_refs: list[str] | None = None,
) -> PolicyRuleEvaluationResult:
    return PolicyRuleEvaluationResult(
        rule_id=str(rule["rule_id"]),
        status="READY",
        severity=str(rule.get("severity") or "REVIEW_REQUIRED"),
        outcome=outcome,
        evidence_refs=evidence_refs or list(list_at(rule, "required_evidence_fields")),
        source_authority_refs=source_authority_refs or source_refs_for_rule(rule),
        reason_codes=[f"{rule['rule_id']}_READY"],
    )


def rule_pending(
    rule: dict[str, Any],
    *,
    outcome: str,
    missing_evidence: list[str],
    reason_codes: list[str],
    required_actions: list[str],
    evidence_refs: list[str] | None = None,
    source_authority_refs: list[str] | None = None,
) -> PolicyRuleEvaluationResult:
    return PolicyRuleEvaluationResult(
        rule_id=str(rule["rule_id"]),
        status="PENDING_REVIEW",
        severity=str(rule.get("severity") or "REVIEW_REQUIRED"),
        outcome=outcome,
        evidence_refs=evidence_refs or list(list_at(rule, "required_evidence_fields")),
        source_authority_refs=source_authority_refs or source_refs_for_rule(rule),
        missing_evidence=unique_strings(missing_evidence),
        reason_codes=unique_strings(reason_codes),
        required_actions=unique_strings(required_actions),
    )


def rule_blocked(
    rule: dict[str, Any],
    *,
    outcome: str,
    missing_evidence: list[str],
    reason_codes: list[str],
    required_actions: list[str],
) -> PolicyRuleEvaluationResult:
    return PolicyRuleEvaluationResult(
        rule_id=str(rule["rule_id"]),
        status="BLOCKED",
        severity=str(rule.get("severity") or "BLOCKING"),
        outcome=outcome,
        evidence_refs=list(list_at(rule, "required_evidence_fields")),
        source_authority_refs=source_refs_for_rule(rule),
        missing_evidence=unique_strings(missing_evidence),
        reason_codes=unique_strings(reason_codes),
        required_actions=unique_strings(required_actions),
    )


def source_refs_for_rule(rule: dict[str, Any]) -> list[str]:
    refs = []
    for field in list_at(rule, "required_evidence_fields"):
        field_key = str(field)
        if field_key.startswith("policy_source_readiness."):
            refs.append("lotus-advise:policy_source_readiness")
        elif field_key.startswith(("fee_", "conflict_", "product_document_")):
            refs.append("lotus-advise:proposal_artifact_policy_evidence")
        elif field_key.startswith("risk_"):
            refs.append(f"lotus-risk:{field_key}")
        else:
            refs.append(f"lotus-core:{field_key}")
    return unique_strings(refs)


def unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


__all__ = [
    "rule_blocked",
    "rule_pending",
    "rule_ready",
    "source_refs_for_rule",
    "unique_strings",
]
