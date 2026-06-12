from decimal import Decimal
from typing import Any, Dict

from src.core.advisory.policy_context import (
    client_context_available,
    mandate_context_available,
)
from src.core.engine_options_models import EngineOptions
from src.core.portfolio_models import ShelfEntry
from src.core.simulation_state_models import SimulatedState

from .suitability_policy import (
    EPSILON,
    HIGH,
    MEDIUM,
    IssueCandidate,
    to_instrument_weight_map,
)


def trade_field(trade: Any, field: str) -> Any:
    if isinstance(trade, dict):
        return trade.get(field)
    return getattr(trade, field, None)


def append_governance_trade_attempt_issues(
    *,
    after_issues: Dict[str, IssueCandidate],
    before: SimulatedState,
    after: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    proposed_trades: list[Any],
    options: EngineOptions,
    **_: Any,
) -> None:
    before_weights = to_instrument_weight_map(before)
    after_weights = to_instrument_weight_map(after)

    for instrument_id in _buy_instrument_ids(proposed_trades):
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        issue = _governance_trade_attempt_issue(
            instrument_id=instrument_id,
            shelf_entry=shelf_entry,
            before_weights=before_weights,
            after_weights=after_weights,
            options=options,
        )
        if issue is not None:
            after_issues[issue.issue_key] = issue


def append_product_complexity_issues(
    *,
    after_issues: Dict[str, IssueCandidate],
    before: SimulatedState,
    after: SimulatedState,
    shelf_by_instrument: Dict[str, ShelfEntry],
    proposed_trades: list[Any],
    policy_context: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    before_weights = to_instrument_weight_map(before)
    after_weights = to_instrument_weight_map(after)
    buy_attempts = set(_buy_instrument_ids(proposed_trades))

    for instrument_id in sorted(set(after_weights) | buy_attempts):
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        if not _requires_product_complexity_evidence(shelf_entry, policy_context):
            continue
        before_weight = before_weights.get(instrument_id, Decimal("0"))
        after_weight = after_weights.get(instrument_id, Decimal("0"))
        if not _is_product_complexity_exposure_increase(
            instrument_id=instrument_id,
            buy_attempts=buy_attempts,
            before_weight=before_weight,
            after_weight=after_weight,
        ):
            continue
        issue = _product_complexity_issue(
            instrument_id=instrument_id,
            product_complexity=_product_complexity(shelf_entry),
            before_weight=before_weight,
            after_weight=after_weight,
        )
        after_issues[issue.issue_key] = issue


def append_restricted_product_mandate_context_issues(
    *,
    after_issues: Dict[str, IssueCandidate],
    shelf_by_instrument: Dict[str, ShelfEntry],
    proposed_trades: list[Any],
    policy_context: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    if not _requires_restricted_product_mandate_context(policy_context):
        return

    for instrument_id in _buy_instrument_ids(proposed_trades):
        issue = _restricted_product_mandate_context_issue_for_instrument(
            instrument_id,
            shelf_by_instrument,
        )
        if issue is not None:
            after_issues[issue.issue_key] = issue


def _buy_instrument_ids(proposed_trades: list[Any]) -> tuple[str, ...]:
    instrument_ids: list[str] = []
    for trade in proposed_trades:
        if trade_field(trade, "side") != "BUY":
            continue
        instrument_id = trade_field(trade, "instrument_id")
        if instrument_id:
            instrument_ids.append(str(instrument_id))
    return tuple(instrument_ids)


def _governance_trade_attempt_issue(
    *,
    instrument_id: str,
    shelf_entry: ShelfEntry,
    before_weights: dict[str, Decimal],
    after_weights: dict[str, Decimal],
    options: EngineOptions,
) -> IssueCandidate | None:
    if shelf_entry.status == "SELL_ONLY":
        return _sell_only_buy_attempt_issue(
            instrument_id=instrument_id,
            shelf_entry=shelf_entry,
            before_weights=before_weights,
            after_weights=after_weights,
        )
    if shelf_entry.status == "RESTRICTED":
        return _restricted_buy_attempt_issue(
            instrument_id=instrument_id,
            shelf_entry=shelf_entry,
            before_weights=before_weights,
            after_weights=after_weights,
            options=options,
        )
    return None


def _sell_only_buy_attempt_issue(
    *,
    instrument_id: str,
    shelf_entry: ShelfEntry,
    before_weights: dict[str, Decimal],
    after_weights: dict[str, Decimal],
) -> IssueCandidate:
    issue_key = f"GOVERNANCE|{instrument_id}|{shelf_entry.status}"
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="SUIT_GOVERNANCE_SELL_ONLY_INCREASE",
        dimension="GOVERNANCE",
        severity=HIGH,
        summary=f"Proposal BUY attempts to increase SELL_ONLY instrument {instrument_id}.",
        details=_governance_weight_details(
            instrument_id=instrument_id,
            shelf_entry=shelf_entry,
            before_weights=before_weights,
            after_weights=after_weights,
        ),
        classification="NEW",
        remediation="Remove the SELL_ONLY buy or obtain explicit product-control approval.",
        approval_implication="COMPLIANCE_REVIEW",
    )


def _restricted_buy_attempt_issue(
    *,
    instrument_id: str,
    shelf_entry: ShelfEntry,
    before_weights: dict[str, Decimal],
    after_weights: dict[str, Decimal],
    options: EngineOptions,
) -> IssueCandidate:
    allowed_severity = MEDIUM if options.allow_restricted else HIGH
    issue_key = f"GOVERNANCE|{instrument_id}|{shelf_entry.status}"
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="SUIT_GOVERNANCE_RESTRICTED_INCREASE",
        dimension="GOVERNANCE",
        severity=allowed_severity,
        summary=f"Proposal BUY attempts to increase RESTRICTED instrument {instrument_id}.",
        details={
            **_governance_weight_details(
                instrument_id=instrument_id,
                shelf_entry=shelf_entry,
                before_weights=before_weights,
                after_weights=after_weights,
            ),
            "allow_restricted": str(options.allow_restricted).lower(),
        },
        classification="NEW",
        remediation="Document the restricted-product rationale before progressing.",
        approval_implication="COMPLIANCE_REVIEW" if allowed_severity == HIGH else "RISK_REVIEW",
    )


def _governance_weight_details(
    *,
    instrument_id: str,
    shelf_entry: ShelfEntry,
    before_weights: dict[str, Decimal],
    after_weights: dict[str, Decimal],
) -> dict[str, str]:
    return {
        "instrument_id": instrument_id,
        "shelf_status": shelf_entry.status,
        "measured_before": str(before_weights.get(instrument_id, Decimal("0"))),
        "measured_after": str(after_weights.get(instrument_id, Decimal("0"))),
    }


def _requires_product_complexity_evidence(
    shelf_entry: ShelfEntry,
    policy_context: dict[str, Any] | None,
) -> bool:
    if _product_complexity(shelf_entry) not in {"HIGH", "COMPLEX"}:
        return False
    return not client_context_available(policy_context)


def _product_complexity(shelf_entry: ShelfEntry) -> str:
    return str(shelf_entry.attributes.get("product_complexity", "")).upper()


def _is_product_complexity_exposure_increase(
    *,
    instrument_id: str,
    buy_attempts: set[str],
    before_weight: Decimal,
    after_weight: Decimal,
) -> bool:
    if instrument_id in buy_attempts:
        return True
    return bool(after_weight > before_weight + EPSILON)


def _product_complexity_issue(
    *,
    instrument_id: str,
    product_complexity: str,
    before_weight: Decimal,
    after_weight: Decimal,
) -> IssueCandidate:
    issue_key = f"PRODUCT_COMPLEXITY|{instrument_id}"
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="MISSING_CLIENT_PRODUCT_COMPLEXITY_EVIDENCE",
        dimension="PRODUCT",
        severity=HIGH,
        summary=(
            f"Complex product {instrument_id} requires client knowledge and experience "
            "evidence before recommendation."
        ),
        details={
            "instrument_id": instrument_id,
            "product_complexity": product_complexity,
            "measured_before": str(before_weight),
            "measured_after": str(after_weight),
        },
        classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
        remediation="Capture client product-complexity evidence before progressing.",
        approval_implication="CLIENT_CONTEXT_REQUIRED",
    )


def _restricted_product_mandate_context_issue(
    instrument_id: str,
    shelf_entry: ShelfEntry,
) -> IssueCandidate:
    issue_key = f"MANDATE_CONTEXT|{instrument_id}"
    return IssueCandidate(
        issue_key=issue_key,
        issue_id="MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE",
        dimension="PRODUCT",
        severity=HIGH,
        summary=(
            f"Restricted product {instrument_id} requires mandate context before recommendation."
        ),
        details={"instrument_id": instrument_id, "shelf_status": shelf_entry.status},
        classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
        remediation="Capture mandate context for the restricted-product recommendation.",
        approval_implication="MANDATE_EXCEPTION_APPROVAL",
    )


def _requires_restricted_product_mandate_context(
    policy_context: dict[str, Any] | None,
) -> bool:
    return policy_context is not None and not mandate_context_available(policy_context)


def _restricted_product_mandate_context_issue_for_instrument(
    instrument_id: str,
    shelf_by_instrument: dict[str, ShelfEntry],
) -> IssueCandidate | None:
    shelf_entry = shelf_by_instrument.get(instrument_id)
    if shelf_entry is None or shelf_entry.status != "RESTRICTED":
        return None
    return _restricted_product_mandate_context_issue(instrument_id, shelf_entry)
