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


def evaluate_conflict_disclosure_review(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    conflict_evidence = dict_at(evidence_bundle, "conflict_evidence")
    missing_docs = missing_product_documents(evidence_bundle)
    missing, reasons, required_actions = conflict_disclosure_findings(
        conflict_evidence=conflict_evidence,
        missing_docs=missing_docs,
    )
    if material_conflict_present(conflict_evidence):
        return rule_blocked(
            rule,
            outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=unique_strings(required_actions),
        )
    if missing:
        return pending_conflict_disclosure_result(
            rule=rule,
            missing=missing,
            reasons=reasons,
            required_actions=required_actions,
        )
    return ready_conflict_disclosure_result(rule)


def missing_product_documents(evidence_bundle: dict[str, Any]) -> list[str]:
    disclosures = artifact_disclosures(evidence_bundle)
    documented = {
        str(row.get("instrument_id"))
        for row in list_at(disclosures, "product_docs")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    proposed = set(proposed_shelf_rows(evidence_bundle))
    return sorted(proposed - documented)


def artifact_disclosures(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    artifact = dict_at(evidence_bundle, "artifact")
    if artifact:
        return cast(dict[str, Any], dict_at(artifact, "disclosures"))
    return cast(dict[str, Any], dict_at(evidence_bundle, "disclosures"))


def conflict_disclosure_findings(
    *, conflict_evidence: dict[str, Any], missing_docs: list[str]
) -> tuple[list[str], list[str], list[str]]:
    missing: list[str] = []
    reasons: list[str] = []
    required_actions: list[str] = []
    add_missing_conflict_evidence(
        conflict_evidence=conflict_evidence,
        missing=missing,
        reasons=reasons,
        required_actions=required_actions,
    )
    add_material_conflict_review(
        conflict_evidence=conflict_evidence,
        reasons=reasons,
        required_actions=required_actions,
    )
    add_missing_product_document_review(
        missing_docs=missing_docs,
        missing=missing,
        reasons=reasons,
        required_actions=required_actions,
    )
    return missing, reasons, required_actions


def add_missing_conflict_evidence(
    *,
    conflict_evidence: dict[str, Any],
    missing: list[str],
    reasons: list[str],
    required_actions: list[str],
) -> None:
    if conflict_evidence:
        return
    missing.append("conflict_evidence")
    reasons.append("CONFLICT_EVIDENCE_NOT_PROVIDED")
    required_actions.append("REVIEW_CONFLICT_OF_INTEREST")


def add_material_conflict_review(
    *,
    conflict_evidence: dict[str, Any],
    reasons: list[str],
    required_actions: list[str],
) -> None:
    if not material_conflict_present(conflict_evidence):
        return
    reasons.append("MATERIAL_CONFLICT_REQUIRES_SUPERVISORY_REVIEW")
    required_actions.append("SUPERVISORY_CONFLICT_REVIEW")


def add_missing_product_document_review(
    *,
    missing_docs: list[str],
    missing: list[str],
    reasons: list[str],
    required_actions: list[str],
) -> None:
    if not missing_docs:
        return
    missing.extend(f"product_document:{instrument_id}" for instrument_id in missing_docs)
    reasons.append("PRODUCT_DOCUMENTATION_INCOMPLETE_FOR_PROPOSED_TRADES")
    required_actions.extend(
        f"REVIEW_PRODUCT_DOCUMENT:{instrument_id}" for instrument_id in missing_docs
    )


def material_conflict_present(conflict_evidence: dict[str, Any]) -> bool:
    return conflict_evidence.get("material_conflict") is True


def pending_conflict_disclosure_result(
    *,
    rule: dict[str, Any],
    missing: list[str],
    reasons: list[str],
    required_actions: list[str],
) -> PolicyRuleEvaluationResult:
    return rule_pending(
        rule,
        outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
        missing_evidence=unique_strings(missing),
        reason_codes=unique_strings(reasons),
        required_actions=unique_strings(required_actions),
        evidence_refs=["artifact.disclosures.product_docs"],
        source_authority_refs=["lotus-advise:proposal_artifact_disclosures"],
    )


def ready_conflict_disclosure_result(rule: dict[str, Any]) -> PolicyRuleEvaluationResult:
    return rule_ready(
        rule,
        "CONFLICT_AND_PRODUCT_DOCUMENT_EVIDENCE_READY_FOR_REVIEW",
        evidence_refs=["artifact.disclosures.product_docs", "evidence_bundle.conflict_evidence"],
        source_authority_refs=[
            "lotus-advise:proposal_artifact_disclosures",
            "lotus-advise:conflict_evidence",
        ],
    )


__all__ = ["evaluate_conflict_disclosure_review"]
