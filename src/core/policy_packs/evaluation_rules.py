from __future__ import annotations

from typing import Any, cast

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_product_helpers import (
    client_segment_allowed as _client_segment_allowed,
)
from src.core.policy_packs.evaluation_product_helpers import (
    is_complex_or_private_product as _is_complex_or_private,
)
from src.core.policy_packs.evaluation_product_helpers import (
    jurisdiction_allowed as _jurisdiction_allowed,
)
from src.core.policy_packs.evaluation_product_helpers import (
    proposed_shelf_rows as _proposed_shelf_rows,
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
from src.core.proposals.source_readiness_common import dict_at, list_at

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


def _evaluate_sg_product_eligibility(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any], jurisdiction: str, client_segment: str
) -> PolicyRuleEvaluationResult:
    missing: list[str] = []
    reasons: list[str] = []
    blocked_instruments: list[str] = []
    for instrument_id, shelf in _proposed_shelf_rows(evidence_bundle).items():
        if shelf is None:
            missing.append(f"shelf_entry:{instrument_id}")
            reasons.append("PRODUCT_SHELF_ENTRY_MISSING_FOR_PROPOSED_TRADE")
            blocked_instruments.append(instrument_id)
            continue
        if not _jurisdiction_allowed(shelf, jurisdiction):
            reasons.append("PRODUCT_NOT_ELIGIBLE_FOR_JURISDICTION")
            blocked_instruments.append(instrument_id)
        if not _client_segment_allowed(shelf, client_segment):
            reasons.append("PRODUCT_NOT_IN_TARGET_MARKET_FOR_CLIENT_SEGMENT")
            blocked_instruments.append(instrument_id)
    if blocked_instruments:
        return _rule_blocked(
            rule,
            outcome="ELIGIBILITY_REVIEW_REQUIRED",
            missing_evidence=_unique(missing),
            reason_codes=_unique(reasons),
            required_actions=[
                f"REVIEW_PRODUCT_ELIGIBILITY:{instrument_id}"
                for instrument_id in _unique(blocked_instruments)
            ],
        )
    return _rule_ready(
        rule,
        "PRODUCT_ELIGIBILITY_AND_TARGET_MARKET_EVIDENCE_READY",
        evidence_refs=[
            "evidence_bundle.inputs.shelf_entries",
            "evidence_bundle.inputs.proposed_trades",
        ],
        source_authority_refs=["lotus-core:core_product_eligibility_target_market_complexity"],
    )


def _evaluate_sg_complex_product_disclosure(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    complex_instruments = [
        instrument_id
        for instrument_id, shelf in _proposed_shelf_rows(evidence_bundle).items()
        if shelf is not None and _is_complex_or_private(shelf)
    ]
    if not complex_instruments:
        return _rule_ready(
            rule,
            "NO_COMPLEX_PRODUCT_DISCLOSURE_TRIGGER",
            evidence_refs=["evidence_bundle.inputs.shelf_entries"],
            source_authority_refs=["lotus-core:core_product_eligibility_target_market_complexity"],
        )
    return _rule_pending(
        rule,
        outcome="DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED",
        missing_evidence=[
            f"advisor_reviewed_disclosure:{instrument_id}" for instrument_id in complex_instruments
        ]
        + [f"client_consent:{instrument_id}" for instrument_id in complex_instruments],
        reason_codes=["COMPLEX_PRODUCT_DISCLOSURE_AND_CONSENT_REQUIRED"],
        required_actions=[
            f"REVIEW_DISCLOSURE:{instrument_id}" for instrument_id in complex_instruments
        ]
        + [f"CAPTURE_CLIENT_CONSENT:{instrument_id}" for instrument_id in complex_instruments],
        evidence_refs=["evidence_bundle.inputs.shelf_entries"],
        source_authority_refs=["lotus-core:core_product_eligibility_target_market_complexity"],
    )


def _evaluate_best_interest_cost(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    assumptions = _artifact_section(evidence_bundle, "assumptions_and_limits")
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
        return _rule_pending(
            rule,
            outcome="BEST_INTEREST_COST_REASONABLENESS_REVIEW_REQUIRED",
            missing_evidence=_unique(missing),
            reason_codes=["BEST_INTEREST_COST_TAX_FRICTION_EVIDENCE_NOT_MODELED"],
            required_actions=["REVIEW_COST_TAX_AND_EXECUTION_FRICTION"],
        )
    return _rule_ready(
        rule,
        "BEST_INTEREST_COST_TAX_AND_FRICTION_EVIDENCE_READY_FOR_REVIEW",
        evidence_refs=["artifact.assumptions_and_limits"],
        source_authority_refs=["lotus-advise:proposal_artifact_assumptions"],
    )


def _evaluate_conflict_disclosure(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    conflict_evidence = dict_at(evidence_bundle, "conflict_evidence")
    disclosures = _artifact_section(evidence_bundle, "disclosures")
    documented = {
        str(row.get("instrument_id"))
        for row in list_at(disclosures, "product_docs")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    proposed = set(_proposed_shelf_rows(evidence_bundle))
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
        return _rule_blocked(
            rule,
            outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            missing_evidence=_unique(missing),
            reason_codes=_unique(reasons),
            required_actions=_unique(required_actions),
        )
    if missing:
        return _rule_pending(
            rule,
            outcome="CONFLICT_AND_DISCLOSURE_REVIEW_REQUIRED",
            missing_evidence=_unique(missing),
            reason_codes=_unique(reasons),
            required_actions=_unique(required_actions),
            evidence_refs=["artifact.disclosures.product_docs"],
            source_authority_refs=["lotus-advise:proposal_artifact_disclosures"],
        )
    return _rule_ready(
        rule,
        "CONFLICT_AND_PRODUCT_DOCUMENT_EVIDENCE_READY_FOR_REVIEW",
        evidence_refs=["artifact.disclosures.product_docs", "evidence_bundle.conflict_evidence"],
        source_authority_refs=[
            "lotus-advise:proposal_artifact_disclosures",
            "lotus-advise:conflict_evidence",
        ],
    )


def _artifact_section(evidence_bundle: dict[str, Any], section: str) -> dict[str, Any]:
    artifact = dict_at(evidence_bundle, "artifact")
    if artifact:
        return cast(dict[str, Any], dict_at(artifact, section))
    return cast(dict[str, Any], dict_at(evidence_bundle, section))


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
