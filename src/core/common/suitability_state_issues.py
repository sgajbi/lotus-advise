from decimal import Decimal
from typing import Any, Dict

from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import ShelfEntry
from src.core.simulation_state_models import SimulatedState

from .suitability_policy import (
    EPSILON,
    HIGH,
    MEDIUM,
    IssueCandidate,
    _SuitabilityPolicyPack,
    issue_data_quality,
    severity_for_concentration,
    to_cash_weight,
    to_instrument_weight_map,
)


def evaluate_single_position_issues(
    *,
    target_state: SimulatedState,
    options: EngineOptions,
    issue_map: Dict[str, IssueCandidate],
    **_: Any,
) -> None:
    thresholds = options.suitability_thresholds
    target_weights = to_instrument_weight_map(target_state)

    for instrument_id, weight in target_weights.items():
        if weight > thresholds.single_position_max_weight + EPSILON:
            severity = severity_for_concentration(weight, thresholds.single_position_max_weight)
            issue_key = f"SINGLE_POSITION_MAX|{instrument_id}"
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_SINGLE_POSITION_MAX",
                dimension="CONCENTRATION",
                severity=severity,
                summary=(
                    f"Single position {instrument_id} exceeds "
                    f"{thresholds.single_position_max_weight:.2%} cap."
                ),
                details={
                    "instrument_id": instrument_id,
                    "threshold": str(thresholds.single_position_max_weight),
                    "measured": str(weight),
                },
                classification="NEW",
                remediation="Reduce the position weight or rebalance through offsetting trades.",
                approval_implication=("COMPLIANCE_REVIEW" if severity == HIGH else "RISK_REVIEW"),
            )


def evaluate_issuer_issues(
    *,
    target_state: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    options: EngineOptions,
    issue_map: Dict[str, IssueCandidate],
    **_: Any,
) -> None:
    thresholds = options.suitability_thresholds
    target_weights = to_instrument_weight_map(target_state)
    issuer_weights: Dict[str, Decimal] = {}

    for instrument_id, weight in target_weights.items():
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            dq_key = f"DQ|MISSING_SHELF|{instrument_id}"
            issue_map[dq_key] = issue_data_quality(
                issue_key=dq_key,
                summary=f"Shelf enrichment missing for {instrument_id}.",
                details={"instrument_id": instrument_id, "missing_fields": "shelf_entry"},
                severity=thresholds.data_quality_issue_severity,
            )
            continue

        if not shelf_entry.issuer_id:
            dq_key = f"DQ|MISSING_ISSUER|{instrument_id}"
            issue_map[dq_key] = issue_data_quality(
                issue_key=dq_key,
                summary=f"Issuer enrichment missing for {instrument_id}.",
                details={"instrument_id": instrument_id, "missing_fields": "issuer_id"},
                severity=thresholds.data_quality_issue_severity,
            )
            continue

        issuer_weights[shelf_entry.issuer_id] = (
            issuer_weights.get(
                shelf_entry.issuer_id,
                Decimal("0"),
            )
            + weight
        )

    for issuer_id, weight in issuer_weights.items():
        if weight > thresholds.issuer_max_weight + EPSILON:
            severity = severity_for_concentration(weight, thresholds.issuer_max_weight)
            issue_key = f"ISSUER_MAX|{issuer_id}"
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_ISSUER_MAX",
                dimension="ISSUER",
                severity=severity,
                summary=(
                    f"Issuer {issuer_id} exceeds {thresholds.issuer_max_weight:.2%} exposure cap."
                ),
                details={
                    "issuer_id": issuer_id,
                    "threshold": str(thresholds.issuer_max_weight),
                    "measured": str(weight),
                },
                classification="NEW",
                remediation="Reduce issuer concentration or add diversified replacement exposure.",
                approval_implication=("COMPLIANCE_REVIEW" if severity == HIGH else "RISK_REVIEW"),
            )


def evaluate_liquidity_issues(
    *,
    target_state: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    options: EngineOptions,
    issue_map: Dict[str, IssueCandidate],
    **_: Any,
) -> None:
    thresholds = options.suitability_thresholds
    target_weights = to_instrument_weight_map(target_state)
    liquidity_weights: Dict[str, Decimal] = {}

    for instrument_id, weight in target_weights.items():
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        if not shelf_entry.liquidity_tier:
            dq_key = f"DQ|MISSING_LIQUIDITY_TIER|{instrument_id}"
            issue_map[dq_key] = issue_data_quality(
                issue_key=dq_key,
                summary=f"Liquidity tier enrichment missing for {instrument_id}.",
                details={"instrument_id": instrument_id, "missing_fields": "liquidity_tier"},
                severity=thresholds.data_quality_issue_severity,
            )
            continue
        liquidity_weights[shelf_entry.liquidity_tier] = (
            liquidity_weights.get(
                shelf_entry.liquidity_tier,
                Decimal("0"),
            )
            + weight
        )

    for tier, cap in thresholds.max_weight_by_liquidity_tier.items():
        measured = liquidity_weights.get(tier, Decimal("0"))
        if measured > cap + EPSILON:
            severity = severity_for_concentration(measured, cap)
            issue_key = f"LIQUIDITY_MAX|{tier}"
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_LIQUIDITY_MAX",
                dimension="LIQUIDITY",
                severity=severity,
                summary=f"Liquidity tier {tier} exceeds {cap:.2%} exposure cap.",
                details={
                    "liquidity_tier": tier,
                    "threshold": str(cap),
                    "measured": str(measured),
                },
                classification="NEW",
                remediation="Reduce illiquid exposure or increase liquid funding assets.",
                approval_implication="RISK_REVIEW",
            )


def evaluate_governance_holdings_issues(
    *,
    target_state: SimulatedState,
    before_state: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    options: EngineOptions,
    issue_map: Dict[str, IssueCandidate],
    **_: Any,
) -> None:
    before_weights = to_instrument_weight_map(before_state)
    target_weights = to_instrument_weight_map(target_state)
    all_instruments = set(before_weights.keys()) | set(target_weights.keys())

    for instrument_id in sorted(all_instruments):
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        before_weight = before_weights.get(instrument_id, Decimal("0"))
        after_weight = target_weights.get(instrument_id, Decimal("0"))
        status = shelf_entry.status
        issue_key = f"GOVERNANCE|{instrument_id}|{status}"

        if status == "BANNED" and after_weight > EPSILON:
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_BANNED",
                dimension="GOVERNANCE",
                severity=HIGH,
                summary=f"BANNED instrument {instrument_id} is present in the portfolio.",
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": status,
                    "measured": str(after_weight),
                },
                classification="NEW",
                remediation="Remove the banned instrument from the proposal before proceeding.",
                approval_implication="COMPLIANCE_REVIEW",
            )

        if status == "SUSPENDED" and after_weight > EPSILON:
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_SUSPENDED",
                dimension="GOVERNANCE",
                severity=HIGH,
                summary=f"SUSPENDED instrument {instrument_id} is present in the portfolio.",
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": status,
                    "measured": str(after_weight),
                },
                classification="NEW",
                remediation="Hold execution until the suspended instrument is removed or cleared.",
                approval_implication="COMPLIANCE_REVIEW",
            )

        if status == "SELL_ONLY" and after_weight > before_weight + EPSILON:
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_SELL_ONLY_INCREASE",
                dimension="GOVERNANCE",
                severity=HIGH,
                summary=f"SELL_ONLY instrument {instrument_id} increased in proposed state.",
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": status,
                    "measured_before": str(before_weight),
                    "measured_after": str(after_weight),
                },
                classification="NEW",
                remediation="Remove the increase or obtain explicit product-control approval.",
                approval_implication="COMPLIANCE_REVIEW",
            )

        if status == "RESTRICTED" and after_weight > before_weight + EPSILON:
            allowed_severity = MEDIUM if options.allow_restricted else HIGH
            issue_map[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_RESTRICTED_INCREASE",
                dimension="GOVERNANCE",
                severity=allowed_severity,
                summary=(
                    f"RESTRICTED instrument {instrument_id} increased in proposed state"
                    if not options.allow_restricted
                    else f"RESTRICTED instrument {instrument_id} increased under allow_restricted"
                ),
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": status,
                    "allow_restricted": str(options.allow_restricted).lower(),
                    "measured_before": str(before_weight),
                    "measured_after": str(after_weight),
                },
                classification="NEW",
                remediation="Confirm the restricted-product rationale before progressing.",
                approval_implication=(
                    "COMPLIANCE_REVIEW" if allowed_severity == HIGH else "RISK_REVIEW"
                ),
            )


def evaluate_cash_band_issue(
    *,
    target_state: SimulatedState,
    options: EngineOptions,
    issue_map: Dict[str, IssueCandidate],
    **_: Any,
) -> None:
    thresholds = options.suitability_thresholds
    cash_weight = to_cash_weight(target_state)
    if (
        cash_weight < thresholds.cash_band_min_weight - EPSILON
        or cash_weight > thresholds.cash_band_max_weight + EPSILON
    ):
        issue_map["CASH_BAND"] = IssueCandidate(
            issue_key="CASH_BAND",
            issue_id="SUIT_CASH_BAND",
            dimension="CASH",
            severity=MEDIUM,
            summary="Cash weight is outside advisory suitability band.",
            details={
                "threshold_min": str(thresholds.cash_band_min_weight),
                "threshold_max": str(thresholds.cash_band_max_weight),
                "measured": str(cash_weight),
            },
            classification="NEW",
            remediation=(
                "Adjust cash funding so the proposal stays within the cash suitability band."
            ),
            approval_implication="RISK_REVIEW",
        )


def scan_state_issues(
    *,
    target_state: SimulatedState,
    before_state: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    options: EngineOptions,
    policy_pack: _SuitabilityPolicyPack,
) -> Dict[str, IssueCandidate]:
    issue_map: Dict[str, IssueCandidate] = {}
    for evaluator in policy_pack.state_evaluators:
        evaluator(
            target_state=target_state,
            before_state=before_state,
            shelf_by_instrument=shelf_by_instrument,
            options=options,
            issue_map=issue_map,
        )
    return issue_map
