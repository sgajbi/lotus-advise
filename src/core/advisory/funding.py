from decimal import Decimal
from typing import Any

from src.core.advisory.funding_selection import (
    FundingDeficit,
    FundingSelection,
    funding_priority_currencies,
    record_missing_fx_pair,
    select_funding_source,
)
from src.core.common.simulation_shared import (
    apply_fx_spot_to_portfolio,
    ensure_cash_balance,
    quantize_amount_for_currency,
)
from src.core.diagnostics_models import FundingPlanEntry, InsufficientCashEntry
from src.core.order_intent_models import FxSpotIntent, IntentRationale

__all__ = [
    "build_auto_funding_plan",
    "funding_priority_currencies",
    "record_missing_fx_pair",
]

AutoFundingPlanResult = tuple[
    list[FxSpotIntent],
    dict[str, str],
    set[str],
    list[str],
    bool,
]


def build_auto_funding_plan(
    *,
    after_portfolio: Any,
    market_data: Any,
    options: Any,
    buy_intents: list[Any],
    diagnostics: Any,
) -> AutoFundingPlanResult:
    fx_intents: list[FxSpotIntent] = []
    fx_by_currency: dict[str, str] = {}
    unfunded_currencies: set[str] = set()
    hard_failures: list[str] = []
    force_pending_review = False

    if not options.auto_funding or options.funding_mode != "AUTO_FX":
        return (
            fx_intents,
            fx_by_currency,
            unfunded_currencies,
            hard_failures,
            force_pending_review,
        )

    grouped_buys = _group_buy_intents_by_currency(buy_intents)

    for target_currency in sorted(grouped_buys.keys()):
        force_pending_review = (
            _fund_target_currency(
                after_portfolio=after_portfolio,
                market_data=market_data,
                options=options,
                diagnostics=diagnostics,
                target_currency=target_currency,
                buys=grouped_buys[target_currency],
                fx_intents=fx_intents,
                fx_by_currency=fx_by_currency,
                unfunded_currencies=unfunded_currencies,
                hard_failures=hard_failures,
            )
            or force_pending_review
        )

    return (
        fx_intents,
        fx_by_currency,
        unfunded_currencies,
        hard_failures,
        force_pending_review,
    )


def _group_buy_intents_by_currency(buy_intents: list[Any]) -> dict[str, list[Any]]:
    grouped_buys: dict[str, list[Any]] = {}
    for intent in buy_intents:
        grouped_buys.setdefault(intent.notional.currency, []).append(intent)
    return grouped_buys


def _fund_target_currency(
    *,
    after_portfolio: Any,
    market_data: Any,
    options: Any,
    diagnostics: Any,
    target_currency: str,
    buys: list[Any],
    fx_intents: list[FxSpotIntent],
    fx_by_currency: dict[str, str],
    unfunded_currencies: set[str],
    hard_failures: list[str],
) -> bool:
    fx_needed, plan = _target_currency_funding_need(
        after_portfolio=after_portfolio,
        target_currency=target_currency,
        buys=buys,
    )
    if fx_needed <= Decimal("0"):
        diagnostics.funding_plan.append(plan)
        return False

    selected, smallest_deficit = select_funding_source(
        after_portfolio=after_portfolio,
        market_data=market_data,
        options=options,
        diagnostics=diagnostics,
        target_currency=target_currency,
        fx_needed=fx_needed,
        cash_ledger={entry.currency: entry.amount for entry in after_portfolio.cash_balances},
    )
    if selected is None:
        return _record_unfunded_target_currency(
            diagnostics=diagnostics,
            options=options,
            target_currency=target_currency,
            smallest_deficit=smallest_deficit,
            unfunded_currencies=unfunded_currencies,
            hard_failures=hard_failures,
            plan=plan,
        )

    _record_funding_fx_intent(
        after_portfolio=after_portfolio,
        target_currency=target_currency,
        fx_needed=fx_needed,
        selected=selected,
        fx_intents=fx_intents,
        fx_by_currency=fx_by_currency,
        plan=plan,
        diagnostics=diagnostics,
    )
    return False


def _target_currency_funding_need(
    *, after_portfolio: Any, target_currency: str, buys: list[Any]
) -> tuple[Decimal, FundingPlanEntry]:
    required = sum((intent.notional.amount for intent in buys), Decimal("0"))
    available_before_fx = ensure_cash_balance(after_portfolio, target_currency).amount
    fx_needed = max(Decimal("0"), required - available_before_fx)
    return (
        fx_needed,
        FundingPlanEntry(
            target_currency=target_currency,
            required=quantize_amount_for_currency(required, target_currency),
            available_before_fx=quantize_amount_for_currency(available_before_fx, target_currency),
            fx_needed=quantize_amount_for_currency(fx_needed, target_currency),
            fx_pair=None,
            funding_currency=None,
        ),
    )


def _record_unfunded_target_currency(
    *,
    diagnostics: Any,
    options: Any,
    target_currency: str,
    smallest_deficit: FundingDeficit | None,
    unfunded_currencies: set[str],
    hard_failures: list[str],
    plan: FundingPlanEntry,
) -> bool:
    unfunded_currencies.add(target_currency)
    diagnostics.funding_plan.append(plan)
    if diagnostics.missing_fx_pairs:
        return _record_missing_fx_funding_failure(
            diagnostics=diagnostics,
            options=options,
            hard_failures=hard_failures,
        )

    if smallest_deficit is not None:
        diagnostics.insufficient_cash.append(
            InsufficientCashEntry(
                currency=smallest_deficit["currency"],
                deficit=quantize_amount_for_currency(
                    smallest_deficit["deficit"],
                    smallest_deficit["currency"],
                ),
            )
        )
    hard_failures.append("PROPOSAL_INSUFFICIENT_FUNDING_CASH")
    return False


def _record_missing_fx_funding_failure(
    *, diagnostics: Any, options: Any, hard_failures: list[str]
) -> bool:
    if options.block_on_missing_fx:
        hard_failures.append("PROPOSAL_MISSING_FX_FOR_FUNDING")
        return False

    if "PROPOSAL_MISSING_FX_NON_BLOCKING" not in diagnostics.warnings:
        diagnostics.warnings.append("PROPOSAL_MISSING_FX_NON_BLOCKING")
    return True


def _record_funding_fx_intent(
    *,
    after_portfolio: Any,
    target_currency: str,
    fx_needed: Decimal,
    selected: FundingSelection,
    fx_intents: list[FxSpotIntent],
    fx_by_currency: dict[str, str],
    plan: FundingPlanEntry,
    diagnostics: Any,
) -> None:
    fx_intent = FxSpotIntent(
        intent_id=f"oi_fx_{len(fx_intents) + 1}",
        pair=selected["pair"],
        buy_currency=target_currency,
        buy_amount=quantize_amount_for_currency(fx_needed, target_currency),
        sell_currency=selected["funding_currency"],
        sell_amount_estimated=selected["sell_required"],
        dependencies=[],
        rationale=IntentRationale(code="FUNDING", message=f"Fund {target_currency} buys"),
    )
    apply_fx_spot_to_portfolio(after_portfolio, fx_intent)
    fx_intents.append(fx_intent)
    fx_by_currency[target_currency] = fx_intent.intent_id
    plan.fx_pair = selected["pair"]
    plan.funding_currency = selected["funding_currency"]
    diagnostics.funding_plan.append(plan)
