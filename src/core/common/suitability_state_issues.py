from decimal import Decimal
from typing import Any, Dict, Literal

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

SuitabilityWeightBucket = Literal["issuer_id", "liquidity_tier"]


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
    issuer_weights = _aggregate_enriched_weights(
        target_weights=target_weights,
        shelf_by_instrument=shelf_by_instrument,
        bucket="issuer_id",
        missing_shelf=True,
        issue_map=issue_map,
        missing_detail="issuer_id",
        missing_summary_label="Issuer enrichment",
        missing_issue_key_prefix="DQ|MISSING_ISSUER",
        data_quality_severity=thresholds.data_quality_issue_severity,
    )

    for issuer_id, weight in issuer_weights.items():
        if weight > thresholds.issuer_max_weight + EPSILON:
            issue = _issuer_exposure_issue(
                issuer_id=issuer_id,
                weight=weight,
                cap=thresholds.issuer_max_weight,
            )
            issue_map[issue.issue_key] = issue


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
    liquidity_weights = _aggregate_enriched_weights(
        target_weights=target_weights,
        shelf_by_instrument=shelf_by_instrument,
        bucket="liquidity_tier",
        missing_shelf=False,
        issue_map=issue_map,
        missing_detail="liquidity_tier",
        missing_summary_label="Liquidity tier enrichment",
        missing_issue_key_prefix="DQ|MISSING_LIQUIDITY_TIER",
        data_quality_severity=thresholds.data_quality_issue_severity,
    )

    for tier, cap in thresholds.max_weight_by_liquidity_tier.items():
        measured = liquidity_weights.get(tier, Decimal("0"))
        if measured > cap + EPSILON:
            issue = _liquidity_exposure_issue(tier=tier, measured=measured, cap=cap)
            issue_map[issue.issue_key] = issue


def _aggregate_enriched_weights(
    *,
    target_weights: Dict[str, Decimal],
    shelf_by_instrument: Dict[str, ShelfEntry],
    bucket: SuitabilityWeightBucket,
    missing_shelf: bool,
    issue_map: Dict[str, IssueCandidate],
    missing_detail: str,
    missing_summary_label: str,
    missing_issue_key_prefix: str,
    data_quality_severity: str,
) -> Dict[str, Decimal]:
    weights: Dict[str, Decimal] = {}
    for instrument_id, weight in target_weights.items():
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            if missing_shelf:
                _add_missing_shelf_issue(
                    instrument_id=instrument_id,
                    issue_map=issue_map,
                    data_quality_severity=data_quality_severity,
                )
            continue

        bucket_value = getattr(shelf_entry, bucket)
        if not bucket_value:
            _add_missing_enrichment_issue(
                instrument_id=instrument_id,
                issue_map=issue_map,
                missing_detail=missing_detail,
                missing_summary_label=missing_summary_label,
                missing_issue_key_prefix=missing_issue_key_prefix,
                data_quality_severity=data_quality_severity,
            )
            continue

        weights[bucket_value] = weights.get(bucket_value, Decimal("0")) + weight
    return weights


def _add_missing_shelf_issue(
    *,
    instrument_id: str,
    issue_map: Dict[str, IssueCandidate],
    data_quality_severity: str,
) -> None:
    issue_key = f"DQ|MISSING_SHELF|{instrument_id}"
    issue_map[issue_key] = issue_data_quality(
        issue_key=issue_key,
        summary=f"Shelf enrichment missing for {instrument_id}.",
        details={"instrument_id": instrument_id, "missing_fields": "shelf_entry"},
        severity=data_quality_severity,
    )


def _add_missing_enrichment_issue(
    *,
    instrument_id: str,
    issue_map: Dict[str, IssueCandidate],
    missing_detail: str,
    missing_summary_label: str,
    missing_issue_key_prefix: str,
    data_quality_severity: str,
) -> None:
    issue_key = f"{missing_issue_key_prefix}|{instrument_id}"
    issue_map[issue_key] = issue_data_quality(
        issue_key=issue_key,
        summary=f"{missing_summary_label} missing for {instrument_id}.",
        details={"instrument_id": instrument_id, "missing_fields": missing_detail},
        severity=data_quality_severity,
    )


def _issuer_exposure_issue(*, issuer_id: str, weight: Decimal, cap: Decimal) -> IssueCandidate:
    severity = severity_for_concentration(weight, cap)
    issue_key = f"ISSUER_MAX|{issuer_id}"
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="SUIT_ISSUER_MAX",
        dimension="ISSUER",
        severity=severity,
        summary=f"Issuer {issuer_id} exceeds {cap:.2%} exposure cap.",
        details={
            "issuer_id": issuer_id,
            "threshold": str(cap),
            "measured": str(weight),
        },
        classification="NEW",
        remediation="Reduce issuer concentration or add diversified replacement exposure.",
        approval_implication=("COMPLIANCE_REVIEW" if severity == HIGH else "RISK_REVIEW"),
    )


def _liquidity_exposure_issue(
    *,
    tier: str,
    measured: Decimal,
    cap: Decimal,
) -> IssueCandidate:
    severity = severity_for_concentration(measured, cap)
    issue_key = f"LIQUIDITY_MAX|{tier}"
    return IssueCandidate(
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
        issue = _governance_holding_issue(
            instrument_id=instrument_id,
            status=shelf_entry.status,
            before_weight=before_weight,
            after_weight=after_weight,
            allow_restricted=options.allow_restricted,
        )
        if issue is not None:
            issue_map[issue.issue_key] = issue


def _governance_holding_issue(
    *,
    instrument_id: str,
    status: str,
    before_weight: Decimal,
    after_weight: Decimal,
    allow_restricted: bool,
) -> IssueCandidate | None:
    presence_issue = _presence_governance_issue_if_applicable(
        instrument_id=instrument_id,
        status=status,
        after_weight=after_weight,
    )
    if presence_issue is not None:
        return presence_issue
    return _increase_governance_issue_if_applicable(
        instrument_id=instrument_id,
        status=status,
        before_weight=before_weight,
        after_weight=after_weight,
        allow_restricted=allow_restricted,
    )


def _presence_governance_issue_if_applicable(
    *,
    instrument_id: str,
    status: str,
    after_weight: Decimal,
) -> IssueCandidate | None:
    if status not in {"BANNED", "SUSPENDED"} or after_weight <= EPSILON:
        return None
    return _presence_governance_issue(
        instrument_id=instrument_id,
        status=status,
        after_weight=after_weight,
    )


def _increase_governance_issue_if_applicable(
    *,
    instrument_id: str,
    status: str,
    before_weight: Decimal,
    after_weight: Decimal,
    allow_restricted: bool,
) -> IssueCandidate | None:
    if not _holding_increased(before_weight, after_weight):
        return None
    if status == "SELL_ONLY":
        return _sell_only_increase_issue(
            instrument_id=instrument_id,
            before_weight=before_weight,
            after_weight=after_weight,
        )
    if status == "RESTRICTED":
        return _restricted_increase_issue(
            instrument_id=instrument_id,
            before_weight=before_weight,
            after_weight=after_weight,
            allow_restricted=allow_restricted,
        )
    return None


def _holding_increased(before_weight: Decimal, after_weight: Decimal) -> bool:
    return bool(after_weight > before_weight + EPSILON)


def _governance_issue_key(*, instrument_id: str, status: str) -> str:
    return f"GOVERNANCE|{instrument_id}|{status}"


def _presence_governance_issue(
    *,
    instrument_id: str,
    status: str,
    after_weight: Decimal,
) -> IssueCandidate:
    issue_id_by_status = {
        "BANNED": "SUIT_GOVERNANCE_BANNED",
        "SUSPENDED": "SUIT_GOVERNANCE_SUSPENDED",
    }
    remediation_by_status = {
        "BANNED": "Remove the banned instrument from the proposal before proceeding.",
        "SUSPENDED": "Hold execution until the suspended instrument is removed or cleared.",
    }
    return IssueCandidate(
        issue_key=_governance_issue_key(instrument_id=instrument_id, status=status),
        issue_id=issue_id_by_status[status],
        dimension="GOVERNANCE",
        severity=HIGH,
        summary=f"{status} instrument {instrument_id} is present in the portfolio.",
        details={
            "instrument_id": instrument_id,
            "shelf_status": status,
            "measured": str(after_weight),
        },
        classification="NEW",
        remediation=remediation_by_status[status],
        approval_implication="COMPLIANCE_REVIEW",
    )


def _sell_only_increase_issue(
    *,
    instrument_id: str,
    before_weight: Decimal,
    after_weight: Decimal,
) -> IssueCandidate:
    status = "SELL_ONLY"
    return IssueCandidate(
        issue_key=_governance_issue_key(instrument_id=instrument_id, status=status),
        issue_id="SUIT_GOVERNANCE_SELL_ONLY_INCREASE",
        dimension="GOVERNANCE",
        severity=HIGH,
        summary=f"SELL_ONLY instrument {instrument_id} increased in proposed state.",
        details=_governance_increase_details(
            instrument_id=instrument_id,
            status=status,
            before_weight=before_weight,
            after_weight=after_weight,
        ),
        classification="NEW",
        remediation="Remove the increase or obtain explicit product-control approval.",
        approval_implication="COMPLIANCE_REVIEW",
    )


def _restricted_increase_issue(
    *,
    instrument_id: str,
    before_weight: Decimal,
    after_weight: Decimal,
    allow_restricted: bool,
) -> IssueCandidate:
    severity = MEDIUM if allow_restricted else HIGH
    status = "RESTRICTED"
    return IssueCandidate(
        issue_key=_governance_issue_key(instrument_id=instrument_id, status=status),
        issue_id="SUIT_GOVERNANCE_RESTRICTED_INCREASE",
        dimension="GOVERNANCE",
        severity=severity,
        summary=_restricted_increase_summary(
            instrument_id=instrument_id,
            allow_restricted=allow_restricted,
        ),
        details={
            **_governance_increase_details(
                instrument_id=instrument_id,
                status=status,
                before_weight=before_weight,
                after_weight=after_weight,
            ),
            "allow_restricted": str(allow_restricted).lower(),
        },
        classification="NEW",
        remediation="Confirm the restricted-product rationale before progressing.",
        approval_implication="COMPLIANCE_REVIEW" if severity == HIGH else "RISK_REVIEW",
    )


def _governance_increase_details(
    *,
    instrument_id: str,
    status: str,
    before_weight: Decimal,
    after_weight: Decimal,
) -> Dict[str, str]:
    return {
        "instrument_id": instrument_id,
        "shelf_status": status,
        "measured_before": str(before_weight),
        "measured_after": str(after_weight),
    }


def _restricted_increase_summary(*, instrument_id: str, allow_restricted: bool) -> str:
    if allow_restricted:
        return f"RESTRICTED instrument {instrument_id} increased under allow_restricted"
    return f"RESTRICTED instrument {instrument_id} increased in proposed state"


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
