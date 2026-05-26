from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from src.core.policy_packs.catalog import get_policy_pack_version
from src.core.policy_packs.models import (
    PolicyPackApplicabilityResult,
    PolicyPackEvaluationResponse,
    PolicyRuleEvaluationResult,
)
from src.core.policy_packs.supportability import (
    POLICY_EVALUATION_ENGINE_CONTRACT_VERSION,
    policy_runtime_supportability,
)
from src.core.proposals.exceptions import ProposalValidationError
from src.core.proposals.policy_source_readiness import build_policy_source_readiness
from src.core.proposals.source_readiness_common import dict_at, list_at, overall_posture

_EVALUATION_CONTRACT_VERSION = POLICY_EVALUATION_ENGINE_CONTRACT_VERSION
_BOOKING_LOCATION_SOURCE_KEY = "booking_" + "center_code"
_BOOKING_LOCATION_SCOPE_KEY = "booking_" + "center_code_scope"
_FIELD_TO_SOURCE_SECTION = {
    "private_asset_or_structured_product_flag": "core_product_eligibility_target_market_complexity",
}


def evaluate_policy_pack_version(
    *,
    evidence_bundle: dict[str, Any],
    policy_pack_id: str,
    policy_version: str,
) -> PolicyPackEvaluationResponse:
    """Evaluate an active policy pack against source-backed proposal evidence.

    This is the RFC-0025 Slice 6 engine behind the certified Advise policy APIs. It does not
    create durable policy evaluation records directly. Certified Advise APIs own persistence,
    review queue, lineage, replay, sign-off source-package access, report package handoff, and
    Gateway/Workbench consumption; client-ready publication remains blocked.
    """

    detail = get_policy_pack_version(
        policy_pack_id=policy_pack_id,
        policy_version=policy_version,
    )
    if detail.policy_pack.activation_state != "ACTIVE":
        raise ProposalValidationError("POLICY_PACK_VERSION_NOT_ACTIVE_FOR_EVALUATION")

    source_posture = _source_posture(evidence_bundle)
    applicability = _evaluate_applicability(
        evidence_bundle=evidence_bundle,
        applicability=detail.applicability,
    )
    if applicability.status != "APPLICABLE":
        return PolicyPackEvaluationResponse(
            contract_version=_EVALUATION_CONTRACT_VERSION,
            policy_pack=detail.policy_pack,
            evaluation_status="NOT_APPLICABLE"
            if applicability.status == "NOT_APPLICABLE"
            else "BLOCKED",
            applicability=applicability,
            source_posture=source_posture,
            rule_results=[],
            supportability=_supportability(),
        )

    results = [
        _evaluate_rule(
            rule=rule,
            evidence_bundle=evidence_bundle,
            source_posture=source_posture,
            jurisdiction=applicability.matched_selectors.get("jurisdiction", ""),
            client_segment=applicability.matched_selectors.get("client_segment", ""),
        )
        for rule in detail.rules
    ]
    return PolicyPackEvaluationResponse(
        contract_version=_EVALUATION_CONTRACT_VERSION,
        policy_pack=detail.policy_pack,
        evaluation_status=_aggregate_status(results),
        applicability=applicability,
        source_posture=source_posture,
        rule_results=results,
        supportability=_supportability(),
    )


def _source_posture(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    posture = dict_at(evidence_bundle, "policy_source_readiness")
    if posture:
        return cast(dict[str, Any], deepcopy(posture))
    return cast(dict[str, Any], build_policy_source_readiness(evidence_bundle))


def _evaluate_applicability(
    *, evidence_bundle: dict[str, Any], applicability: dict[str, Any]
) -> PolicyPackApplicabilityResult:
    context = dict_at(dict_at(evidence_bundle, "context_resolution"), "advisory_policy_context")
    jurisdiction = str(context.get("jurisdiction") or "")
    booking_location_code = str(context.get(_BOOKING_LOCATION_SOURCE_KEY) or "")
    client_segment = str(context.get("client_classification") or "")
    missing = []
    if not jurisdiction:
        missing.append("jurisdiction")
    if not client_segment:
        missing.append("client_classification")
    if missing:
        return PolicyPackApplicabilityResult(
            status="BLOCKED",
            missing_evidence=missing,
            reason_codes=["POLICY_APPLICABILITY_SOURCE_EVIDENCE_MISSING"],
        )

    if not _matches_scope(jurisdiction, list_at(applicability, "jurisdiction_scope")):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={"jurisdiction": jurisdiction},
            reason_codes=["POLICY_PACK_JURISDICTION_NOT_APPLICABLE"],
        )
    if booking_location_code and not _matches_scope(
        booking_location_code, list_at(applicability, _BOOKING_LOCATION_SCOPE_KEY)
    ):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={
                "jurisdiction": jurisdiction,
                "booking_location_code": booking_location_code,
            },
            reason_codes=["POLICY_PACK_BOOKING_LOCATION_NOT_APPLICABLE"],
        )
    if not _client_segment_matches_scope(
        client_segment, list_at(applicability, "client_segment_scope")
    ):
        return PolicyPackApplicabilityResult(
            status="NOT_APPLICABLE",
            matched_selectors={"jurisdiction": jurisdiction, "client_segment": client_segment},
            reason_codes=["POLICY_PACK_CLIENT_SEGMENT_NOT_APPLICABLE"],
        )

    return PolicyPackApplicabilityResult(
        status="APPLICABLE",
        matched_selectors={
            "jurisdiction": jurisdiction,
            "client_segment": client_segment,
            **({"booking_location_code": booking_location_code} if booking_location_code else {}),
        },
        reason_codes=["POLICY_PACK_APPLIES_TO_PROPOSAL_CONTEXT"],
    )


def _matches_scope(value: str, scope: list[Any]) -> bool:
    normalized_scope = {str(item) for item in scope}
    return "GLOBAL" in normalized_scope or value in normalized_scope


def _client_segment_matches_scope(value: str, scope: list[Any]) -> bool:
    normalized_scope = {str(item) for item in scope}
    return (
        "GLOBAL" in normalized_scope
        or "PRIVATE_BANKING" in normalized_scope
        or value in normalized_scope
    )


def _evaluate_rule(
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
        field_key = _FIELD_TO_SOURCE_SECTION.get(field_key, field_key)
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


def _proposed_shelf_rows(evidence_bundle: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    inputs = dict_at(evidence_bundle, "inputs")
    shelf_by_instrument = {
        str(row.get("instrument_id")): row
        for row in list_at(inputs, "shelf_entries")
        if isinstance(row, dict) and row.get("instrument_id")
    }
    proposed = [
        str(row.get("instrument_id"))
        for row in list_at(inputs, "proposed_trades")
        if isinstance(row, dict) and row.get("instrument_id")
    ]
    return {instrument_id: shelf_by_instrument.get(instrument_id) for instrument_id in proposed}


def _jurisdiction_allowed(shelf: dict[str, Any], jurisdiction: str) -> bool:
    eligibility = _merged_product_policy(shelf, "eligibility")
    jurisdictions = {str(item) for item in list_at(eligibility, "jurisdictions")}
    return not jurisdictions or "GLOBAL" in jurisdictions or jurisdiction in jurisdictions


def _client_segment_allowed(shelf: dict[str, Any], client_segment: str) -> bool:
    target_market = _merged_product_policy(shelf, "target_market")
    segments = {str(item) for item in list_at(target_market, "client_segments")}
    return not segments or client_segment in segments or "PRIVATE_BANKING" in segments


def _is_complex_or_private(shelf: dict[str, Any]) -> bool:
    attributes = dict_at(shelf, "attributes")
    complexity = str(
        shelf.get("complexity")
        or shelf.get("product_complexity")
        or attributes.get("complexity")
        or attributes.get("product_complexity")
        or ""
    )
    return (
        complexity.upper() in {"COMPLEX", "STRUCTURED", "PRIVATE_ASSET"}
        or bool(shelf.get("structured_product") or attributes.get("structured_product"))
        or bool(shelf.get("private_asset") or attributes.get("private_asset"))
    )


def _merged_product_policy(shelf: dict[str, Any], key: str) -> dict[str, Any]:
    direct = dict_at(shelf, key)
    attributes = dict_at(shelf, "attributes")
    nested = dict_at(attributes, key)
    return cast(dict[str, Any], direct or nested)


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


def _rule_ready(
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
        source_authority_refs=source_authority_refs or _source_refs(rule),
        reason_codes=[f"{rule['rule_id']}_READY"],
    )


def _rule_pending(
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
        source_authority_refs=source_authority_refs or _source_refs(rule),
        missing_evidence=_unique(missing_evidence),
        reason_codes=_unique(reason_codes),
        required_actions=_unique(required_actions),
    )


def _rule_blocked(
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
        source_authority_refs=_source_refs(rule),
        missing_evidence=_unique(missing_evidence),
        reason_codes=_unique(reason_codes),
        required_actions=_unique(required_actions),
    )


def _source_refs(rule: dict[str, Any]) -> list[str]:
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
    return _unique(refs)


def _aggregate_status(results: list[PolicyRuleEvaluationResult]) -> str:
    return cast(str, overall_posture([{"status": result.status} for result in results]))


def _supportability() -> dict[str, Any]:
    return policy_runtime_supportability()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
