from __future__ import annotations

from typing import Any, cast

from src.core.policy_packs.evaluation_conflict_disclosure import (
    evaluate_conflict_disclosure_review,
)
from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_result_builders import (
    rule_pending,
    rule_ready,
    unique_strings,
)
from src.core.proposals.source_readiness_common import dict_at


def evaluate_best_interest_cost(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    assumptions = artifact_section(evidence_bundle, "assumptions_and_limits")
    costs = dict_at(assumptions, "costs_and_fees")
    tax = dict_at(assumptions, "tax")
    execution = dict_at(assumptions, "execution")
    missing = []
    if not costs.get("included"):
        missing.extend(["fee_evidence", "cost_evidence"])
    if not tax.get("included"):
        missing.append("tax_evidence")
    if not execution.get("included"):
        missing.append("execution_friction_evidence")
    if missing:
        return rule_pending(
            rule,
            outcome="BEST_INTEREST_COST_REASONABLENESS_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=["BEST_INTEREST_COST_TAX_FRICTION_EVIDENCE_NOT_MODELED"],
            required_actions=["REVIEW_COST_TAX_AND_EXECUTION_FRICTION"],
        )
    return rule_ready(
        rule,
        "BEST_INTEREST_COST_TAX_AND_FRICTION_EVIDENCE_READY_FOR_REVIEW",
        evidence_refs=["artifact.assumptions_and_limits"],
        source_authority_refs=["lotus-advise:proposal_artifact_assumptions"],
    )


def evaluate_conflict_disclosure(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    return evaluate_conflict_disclosure_review(rule=rule, evidence_bundle=evidence_bundle)


def artifact_section(evidence_bundle: dict[str, Any], section: str) -> dict[str, Any]:
    artifact = dict_at(evidence_bundle, "artifact")
    if artifact:
        return cast(dict[str, Any], dict_at(artifact, section))
    return cast(dict[str, Any], dict_at(evidence_bundle, section))


__all__ = [
    "artifact_section",
    "evaluate_best_interest_cost",
    "evaluate_conflict_disclosure",
]
