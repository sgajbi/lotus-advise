from __future__ import annotations

from typing import Any

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_product_rules import (
    evaluate_sg_complex_product_disclosure as _evaluate_sg_complex_product_disclosure,
)
from src.core.policy_packs.evaluation_product_rules import (
    evaluate_sg_product_eligibility as _evaluate_sg_product_eligibility,
)
from src.core.policy_packs.evaluation_result_builders import (
    rule_blocked as _rule_blocked,
)
from src.core.policy_packs.evaluation_result_builders import (
    rule_pending as _rule_pending,
)
from src.core.policy_packs.evaluation_result_builders import (
    rule_ready as _rule_ready,
)
from src.core.policy_packs.evaluation_result_builders import (
    unique_strings as _unique,
)
from src.core.policy_packs.evaluation_review_rules import (
    evaluate_best_interest_cost as _evaluate_best_interest_cost,
)
from src.core.policy_packs.evaluation_review_rules import (
    evaluate_conflict_disclosure as _evaluate_conflict_disclosure,
)
from src.core.proposals.source_readiness_common import list_at

FIELD_TO_SOURCE_SECTION = {
    "private_asset_or_structured_product_flag": "core_product_eligibility_target_market_complexity",
}


def evaluate_policy_rule(
    *,
    rule: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_posture: dict[str, Any],
    jurisdiction: str,
    client_segment: str,
) -> PolicyRuleEvaluationResult:
    rule_id = str(rule["rule_id"])
    required = _required_source_result(rule=rule, source_posture=source_posture)
    if required is not None:
        return required
    if rule_id == "GLOBAL_SOURCE_READINESS_REQUIRED":
        return _rule_ready(rule, "SOURCE_EVIDENCE_READY_FOR_POLICY_REVIEW")
    if rule_id == "GLOBAL_MANDATE_RESTRICTIONS_REVIEW":
        return _evaluate_mandate_rule(rule=rule, source_posture=source_posture)
    if rule_id == "SG_AI_PRODUCT_ELIGIBILITY_REVIEW":
        return _evaluate_sg_product_eligibility(
            rule=rule,
            evidence_bundle=evidence_bundle,
            jurisdiction=jurisdiction,
            client_segment=client_segment,
        )
    if rule_id == "SG_COMPLEX_PRODUCT_DISCLOSURE_REVIEW":
        return _evaluate_sg_complex_product_disclosure(rule=rule, evidence_bundle=evidence_bundle)
    if rule_id == "SG_BEST_INTEREST_COST_REVIEW":
        return _evaluate_best_interest_cost(rule=rule, evidence_bundle=evidence_bundle)
    if rule_id == "SG_CONFLICT_REVIEW":
        return _evaluate_conflict_disclosure(rule=rule, evidence_bundle=evidence_bundle)
    return _rule_pending(
        rule,
        outcome=str(rule.get("outcome_mapping") or "POLICY_RULE_REVIEW_REQUIRED"),
        missing_evidence=[],
        reason_codes=["POLICY_RULE_EVALUATOR_NOT_SPECIALIZED"],
        required_actions=["POLICY_STEWARD_REVIEW"],
    )


def _required_source_result(
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
                for source_section in _sections_with_status(source_posture, "BLOCKED"):
                    missing.extend(
                        str(item) for item in list_at(source_section, "missing_evidence")
                    )
                    reasons.extend(str(item) for item in list_at(source_section, "reason_codes"))
            elif source_posture.get("overall_posture") == "PENDING_REVIEW":
                pending = True
                for source_section in _sections_with_status(source_posture, "PENDING_REVIEW"):
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
        return _rule_blocked(
            rule,
            outcome="SOURCE_EVIDENCE_BLOCKED",
            missing_evidence=_unique(missing),
            reason_codes=_unique(reasons),
            required_actions=["RESTORE_SOURCE_OWNER_EVIDENCE"],
        )
    if missing or pending:
        return _rule_pending(
            rule,
            outcome="SOURCE_EVIDENCE_REVIEW_REQUIRED",
            missing_evidence=_unique(missing),
            reason_codes=_unique(reasons),
            required_actions=["REVIEW_SOURCE_OWNER_EVIDENCE"],
        )
    return None


def _evaluate_mandate_rule(
    *, rule: dict[str, Any], source_posture: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    section = _section(source_posture, "core_mandate_objectives_restrictions")
    restrictions = list_at(section, "evidence_refs")
    return _rule_ready(
        rule,
        "MANDATE_OBJECTIVES_AND_RESTRICTIONS_READY_FOR_ADVISOR_REVIEW",
        evidence_refs=restrictions,
        source_authority_refs=["lotus-core:core_mandate_objectives_restrictions"],
    )


def _section(source_posture: dict[str, Any], key: str) -> dict[str, Any]:
    for section in list_at(source_posture, "sections"):
        if isinstance(section, dict) and section.get("key") == key:
            return section
    return {}


def _sections_with_status(source_posture: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return [
        section
        for section in list_at(source_posture, "sections")
        if isinstance(section, dict) and section.get("status") == status
    ]
