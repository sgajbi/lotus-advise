from decimal import Decimal

from src.core.models import DroppedIntent, Money


def calculate_turnover_score(intent, portfolio_value_base):
    if portfolio_value_base <= Decimal("0"):
        return Decimal("0")
    return abs(intent.notional_base.amount) / portfolio_value_base


def apply_turnover_limit(
    *,
    intents,
    options,
    portfolio_value_base,
    base_currency,
    diagnostics,
):
    if options.max_turnover_pct is None:
        return intents

    budget = portfolio_value_base * options.max_turnover_pct
    proposed = sum(abs(intent.notional_base.amount) for intent in intents)
    if proposed <= budget:
        return intents

    ranked = sorted(
        intents,
        key=lambda intent: (
            -calculate_turnover_score(intent, portfolio_value_base),
            abs(intent.notional_base.amount),
            intent.instrument_id,
            intent.intent_id,
        ),
    )

    selected = []
    used = Decimal("0")
    for intent in ranked:
        notional_abs = abs(intent.notional_base.amount)
        score = calculate_turnover_score(intent, portfolio_value_base)
        if used + notional_abs <= budget:
            selected.append(intent)
            used += notional_abs
            continue

        diagnostics.dropped_intents.append(
            DroppedIntent(
                instrument_id=intent.instrument_id,
                reason="TURNOVER_LIMIT",
                potential_notional=Money(amount=notional_abs, currency=base_currency),
                score=score,
            )
        )

    if diagnostics.dropped_intents:
        diagnostics.warnings.append("PARTIAL_REBALANCE_TURNOVER_LIMIT")

    return selected
