from __future__ import annotations

from typing import Any

from src.core.policy_packs.evaluation_models import PolicyRuleEvaluationResult
from src.core.policy_packs.evaluation_product_helpers import (
    client_segment_allowed,
    is_complex_or_private_product,
    jurisdiction_allowed,
    proposed_shelf_rows,
)
from src.core.policy_packs.evaluation_result_builders import (
    rule_blocked,
    rule_pending,
    rule_ready,
    unique_strings,
)

_PRODUCT_COMPLEXITY_SOURCE_REF = "lotus-core:core_product_eligibility_target_market_complexity"
_PRODUCT_SHELF_EVIDENCE_REF = "evidence_bundle.inputs.shelf_entries"
_PROPOSED_TRADES_EVIDENCE_REF = "evidence_bundle.inputs.proposed_trades"


def _product_eligibility_issues(
    *, evidence_bundle: dict[str, Any], jurisdiction: str, client_segment: str
) -> tuple[list[str], list[str], list[str]]:
    missing: list[str] = []
    reasons: list[str] = []
    blocked_instruments: list[str] = []
    for instrument_id, shelf in proposed_shelf_rows(evidence_bundle).items():
        if shelf is None:
            missing.append(f"shelf_entry:{instrument_id}")
            reasons.append("PRODUCT_SHELF_ENTRY_MISSING_FOR_PROPOSED_TRADE")
            blocked_instruments.append(instrument_id)
            continue
        if not jurisdiction_allowed(shelf, jurisdiction):
            reasons.append("PRODUCT_NOT_ELIGIBLE_FOR_JURISDICTION")
            blocked_instruments.append(instrument_id)
        if not client_segment_allowed(shelf, client_segment):
            reasons.append("PRODUCT_NOT_IN_TARGET_MARKET_FOR_CLIENT_SEGMENT")
            blocked_instruments.append(instrument_id)
    return missing, reasons, blocked_instruments


def _product_eligibility_required_actions(blocked_instruments: list[str]) -> list[str]:
    return [
        f"REVIEW_PRODUCT_ELIGIBILITY:{instrument_id}"
        for instrument_id in unique_strings(blocked_instruments)
    ]


def _complex_disclosure_instrument_ids(evidence_bundle: dict[str, Any]) -> list[str]:
    return [
        instrument_id
        for instrument_id, shelf in proposed_shelf_rows(evidence_bundle).items()
        if shelf is not None and is_complex_or_private_product(shelf)
    ]


def _complex_disclosure_missing_evidence(instrument_ids: list[str]) -> list[str]:
    return [f"advisor_reviewed_disclosure:{instrument_id}" for instrument_id in instrument_ids] + [
        f"client_consent:{instrument_id}" for instrument_id in instrument_ids
    ]


def _complex_disclosure_required_actions(instrument_ids: list[str]) -> list[str]:
    return [f"REVIEW_DISCLOSURE:{instrument_id}" for instrument_id in instrument_ids] + [
        f"CAPTURE_CLIENT_CONSENT:{instrument_id}" for instrument_id in instrument_ids
    ]


def evaluate_sg_product_eligibility(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any], jurisdiction: str, client_segment: str
) -> PolicyRuleEvaluationResult:
    missing, reasons, blocked_instruments = _product_eligibility_issues(
        evidence_bundle=evidence_bundle,
        jurisdiction=jurisdiction,
        client_segment=client_segment,
    )
    if blocked_instruments:
        return rule_blocked(
            rule,
            outcome="ELIGIBILITY_REVIEW_REQUIRED",
            missing_evidence=unique_strings(missing),
            reason_codes=unique_strings(reasons),
            required_actions=_product_eligibility_required_actions(blocked_instruments),
        )
    return rule_ready(
        rule,
        "PRODUCT_ELIGIBILITY_AND_TARGET_MARKET_EVIDENCE_READY",
        evidence_refs=[
            _PRODUCT_SHELF_EVIDENCE_REF,
            _PROPOSED_TRADES_EVIDENCE_REF,
        ],
        source_authority_refs=[_PRODUCT_COMPLEXITY_SOURCE_REF],
    )


def evaluate_sg_complex_product_disclosure(
    *, rule: dict[str, Any], evidence_bundle: dict[str, Any]
) -> PolicyRuleEvaluationResult:
    complex_instruments = _complex_disclosure_instrument_ids(evidence_bundle)
    if not complex_instruments:
        return rule_ready(
            rule,
            "NO_COMPLEX_PRODUCT_DISCLOSURE_TRIGGER",
            evidence_refs=[_PRODUCT_SHELF_EVIDENCE_REF],
            source_authority_refs=[_PRODUCT_COMPLEXITY_SOURCE_REF],
        )
    return rule_pending(
        rule,
        outcome="DISCLOSURE_AND_CONSENT_REVIEW_REQUIRED",
        missing_evidence=_complex_disclosure_missing_evidence(complex_instruments),
        reason_codes=["COMPLEX_PRODUCT_DISCLOSURE_AND_CONSENT_REQUIRED"],
        required_actions=_complex_disclosure_required_actions(complex_instruments),
        evidence_refs=[_PRODUCT_SHELF_EVIDENCE_REF],
        source_authority_refs=[_PRODUCT_COMPLEXITY_SOURCE_REF],
    )


__all__ = [
    "evaluate_sg_complex_product_disclosure",
    "evaluate_sg_product_eligibility",
]
