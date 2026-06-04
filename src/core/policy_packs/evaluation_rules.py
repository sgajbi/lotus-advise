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
    rule_pending as _rule_pending,
)
from src.core.policy_packs.evaluation_result_builders import (
    rule_ready as _rule_ready,
)
from src.core.policy_packs.evaluation_review_rules import (
    evaluate_best_interest_cost as _evaluate_best_interest_cost,
)
from src.core.policy_packs.evaluation_review_rules import (
    evaluate_conflict_disclosure as _evaluate_conflict_disclosure,
)
from src.core.policy_packs.evaluation_source_rules import (
    evaluate_mandate_rule as _evaluate_mandate_rule,
)
from src.core.policy_packs.evaluation_source_rules import (
    required_source_result as _required_source_result,
)


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
