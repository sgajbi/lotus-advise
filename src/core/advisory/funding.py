from decimal import Decimal
from typing import Any

from src.core.advisory.funding_selection import (
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


def build_auto_funding_plan(
    *,
    after_portfolio: Any,
    market_data: Any,
    options: Any,
    buy_intents: list[Any],
    diagnostics: Any,
) -> tuple[
    list[FxSpotIntent],
    dict[str, str],
    set[str],
    list[str],
    bool,
]:
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

    grouped_buys: dict[str, list[Any]] = {}
    for intent in buy_intents:
        grouped_buys.setdefault(intent.notional.currency, []).append(intent)

    for target_currency in sorted(grouped_buys.keys()):
        buys = grouped_buys[target_currency]
        required = sum((intent.notional.amount for intent in buys), Decimal("0"))
        available_before_fx = ensure_cash_balance(after_portfolio, target_currency).amount
        fx_needed = max(Decimal("0"), required - available_before_fx)

        plan = FundingPlanEntry(
            target_currency=target_currency,
            required=quantize_amount_for_currency(required, target_currency),
            available_before_fx=quantize_amount_for_currency(available_before_fx, target_currency),
            fx_needed=quantize_amount_for_currency(fx_needed, target_currency),
            fx_pair=None,
            funding_currency=None,
        )

        if fx_needed <= Decimal("0"):
            diagnostics.funding_plan.append(plan)
            continue

        cash_ledger = {entry.currency: entry.amount for entry in after_portfolio.cash_balances}
        selected, smallest_deficit = select_funding_source(
            after_portfolio=after_portfolio,
            market_data=market_data,
            options=options,
            diagnostics=diagnostics,
            target_currency=target_currency,
            fx_needed=fx_needed,
            cash_ledger=cash_ledger,
        )

        if selected is None:
            if diagnostics.missing_fx_pairs and not options.block_on_missing_fx:
                force_pending_review = True
                if "PROPOSAL_MISSING_FX_NON_BLOCKING" not in diagnostics.warnings:
                    diagnostics.warnings.append("PROPOSAL_MISSING_FX_NON_BLOCKING")
                unfunded_currencies.add(target_currency)
                diagnostics.funding_plan.append(plan)
                continue

            if diagnostics.missing_fx_pairs and options.block_on_missing_fx:
                hard_failures.append("PROPOSAL_MISSING_FX_FOR_FUNDING")
                unfunded_currencies.add(target_currency)
                diagnostics.funding_plan.append(plan)
                continue

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
            unfunded_currencies.add(target_currency)
            diagnostics.funding_plan.append(plan)
            continue

        fx_intent_id = f"oi_fx_{len(fx_intents) + 1}"
        fx_buy_amount = quantize_amount_for_currency(fx_needed, target_currency)
        fx_intent = FxSpotIntent(
            intent_id=fx_intent_id,
            pair=selected["pair"],
            buy_currency=target_currency,
            buy_amount=fx_buy_amount,
            sell_currency=selected["funding_currency"],
            sell_amount_estimated=selected["sell_required"],
            dependencies=[],
            rationale=IntentRationale(code="FUNDING", message=f"Fund {target_currency} buys"),
        )

        apply_fx_spot_to_portfolio(after_portfolio, fx_intent)
        fx_intents.append(fx_intent)
        fx_by_currency[target_currency] = fx_intent_id

        plan.fx_pair = selected["pair"]
        plan.funding_currency = selected["funding_currency"]
        diagnostics.funding_plan.append(plan)

    return (
        fx_intents,
        fx_by_currency,
        unfunded_currencies,
        hard_failures,
        force_pending_review,
    )
