from __future__ import annotations

from typing import Any, cast

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_product_helpers import proposed_shelf_rows
from src.core.policy_packs.evaluation_result_builders import (
    rule_blocked,
    rule_pending,
    rule_ready,
    unique_strings,
)
from src.core.proposals.source_readiness_common import dict_at, list_at


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
    conflict_evidence = dict_at(evidence_bundle, "conflict_evidence")
    disclosures = artifact_section(evidence_bundle, "disclosures")
    documented = {
        str(row.get("instrument_id"))
        for row in list_at(disclosures, "product_docs")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    proposed = set(proposed_shelf_rows(evidence_bundle))
    missing_docs = sorted(proposed - documented)
    missing: list[str] = []
    reasons: list[str] = []
    required_actions: list[str] = []
    if not conflict_evidence:
        missing.append("conflict_evidence")
        reasons.append("CONFLICT_EVIDENCE_NOT_PROVIDED")
        required_actions.append("REVIEW_CONFLICT_OF_INTEREST")
    if conflict_evidence.get("material_conflict") is True:
        reasons.append("MATERIAL_CONFLICT_REQUIRES_SUPERVISORY_REVIEW")
        required_actions.append("SUPERVISORY_CONFLICT_REVIEW")
    if missing_docs:
        missing.extend(f"product_document:{instrument_id}" for instrument_id in missing_docs)
        reasons.append("PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES")
        required_actions.extend(
            f"REVIEW_PRODUCT_DOCUMENT:{instrument_id}" for instrument_id in missing_docs
        )
    if conflict_evidence.get("material_conflict") is True:
        return rule_blocked(
            rule,
            outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=unique_strings(required_actions),
        )
    if missing:
        return rule_pending(
            rule,
            outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=unique_strings(required_actions),
            evidence_refs=["artifact.disclosures.product_docs"],
            source_authority_refs=["lotus-advise:proposal_artifact_disclosures"],
        )
    return rule_ready(
        rule,
        "CONFLICT_AND_PRODUCT_DOCUMENT_EVIDENCE_READY_FOR_REVIEW",
        evidence_refs=["artifact.disclosures.product_docs", "evidence_bundle.conflict_evidence"],
        source_authority_refs=[
            "lotus-advise:proposal_artifact_disclosures",
            "lotus-advise:conflict_evidence",
        ],
    )


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
