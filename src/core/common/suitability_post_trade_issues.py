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

    for trade in proposed_trades:
        if trade_field(trade, "side") != "BUY":
            continue
        instrument_id = trade_field(trade, "instrument_id")
        if not instrument_id:
            continue
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        issue_key = f"GOVERNANCE|{instrument_id}|{shelf_entry.status}"
        if shelf_entry.status == "SELL_ONLY":
            after_issues[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_SELL_ONLY_INCREASE",
                dimension="GOVERNANCE",
                severity=HIGH,
                summary=f"Proposal BUY attempts to increase SELL_ONLY instrument {instrument_id}.",
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": shelf_entry.status,
                    "measured_before": str(before_weights.get(instrument_id, Decimal("0"))),
                    "measured_after": str(after_weights.get(instrument_id, Decimal("0"))),
                },
                classification="NEW",
                remediation="Remove the SELL_ONLY buy or obtain explicit product-control approval.",
                approval_implication="COMPLIANCE_REVIEW",
            )
        if shelf_entry.status == "RESTRICTED":
            allowed_severity = MEDIUM if options.allow_restricted else HIGH
            after_issues[issue_key] = IssueCandidate(
                issue_key=issue_key,
                issue_id="SUIT_GOVERNANCE_RESTRICTED_INCREASE",
                dimension="GOVERNANCE",
                severity=allowed_severity,
                summary=f"Proposal BUY attempts to increase RESTRICTED instrument {instrument_id}.",
                details={
                    "instrument_id": instrument_id,
                    "shelf_status": shelf_entry.status,
                    "allow_restricted": str(options.allow_restricted).lower(),
                    "measured_before": str(before_weights.get(instrument_id, Decimal("0"))),
                    "measured_after": str(after_weights.get(instrument_id, Decimal("0"))),
                },
                classification="NEW",
                remediation="Document the restricted-product rationale before progressing.",
                approval_implication=(
                    "COMPLIANCE_REVIEW" if allowed_severity == HIGH else "RISK_REVIEW"
                ),
            )


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
    buy_attempts = {
        str(trade_field(trade, "instrument_id"))
        for trade in proposed_trades
        if trade_field(trade, "side") == "BUY" and trade_field(trade, "instrument_id")
    }

    for instrument_id in sorted(set(after_weights) | buy_attempts):
        shelf_entry = shelf_by_instrument.get(instrument_id)
        if shelf_entry is None:
            continue
        complexity = str(shelf_entry.attributes.get("product_complexity", "")).upper()
        if complexity not in {"HIGH", "COMPLEX"}:
            continue
        if client_context_available(policy_context):
            continue
        before_weight = before_weights.get(instrument_id, Decimal("0"))
        after_weight = after_weights.get(instrument_id, Decimal("0"))
        if instrument_id not in buy_attempts and after_weight <= before_weight + EPSILON:
            continue
        issue_key = f"PRODUCT_COMPLEXITY|{instrument_id}"
        after_issues[issue_key] = IssueCandidate(
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
                "product_complexity": complexity,
                "measured_before": str(before_weight),
                "measured_after": str(after_weight),
            },
            classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
            remediation="Capture client product-complexity evidence before progressing.",
            approval_implication="CLIENT_CONTEXT_REQUIRED",
        )


def append_restricted_product_mandate_context_issues(
    *,
    after_issues: Dict[str, IssueCandidate],
    shelf_by_instrument: Dict[str, ShelfEntry],
    proposed_trades: list[Any],
    policy_context: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    if policy_context is None or mandate_context_available(policy_context):
        return

    for trade in proposed_trades:
        if trade_field(trade, "side") != "BUY":
            continue
        instrument_id = trade_field(trade, "instrument_id")
        if not instrument_id:
            continue
        shelf_entry = shelf_by_instrument.get(str(instrument_id))
        if shelf_entry is None or shelf_entry.status != "RESTRICTED":
            continue
        issue_key = f"MANDATE_CONTEXT|{instrument_id}"
        after_issues[issue_key] = IssueCandidate(
            issue_key=issue_key,
            issue_id="MISSING_MANDATE_RESTRICTED_PRODUCT_EVIDENCE",
            dimension="PRODUCT",
            severity=HIGH,
            summary=(
                f"Restricted product {instrument_id} requires mandate context before "
                "recommendation."
            ),
            details={"instrument_id": str(instrument_id), "shelf_status": shelf_entry.status},
            classification="UNKNOWN_DUE_TO_MISSING_EVIDENCE",
            remediation="Capture mandate context for the restricted-product recommendation.",
            approval_implication="MANDATE_EXCEPTION_APPROVAL",
        )
