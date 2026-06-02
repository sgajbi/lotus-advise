from decimal import Decimal
from typing import Any, Optional, TypedDict

from src.core.common.simulation_shared import (
    ensure_cash_balance,
    quantize_amount_for_currency,
)
from src.core.valuation import get_fx_rate


class FundingSelection(TypedDict):
    pair: str
    rate: Decimal
    funding_currency: str
    sell_required: Decimal


class FundingDeficit(TypedDict):
    currency: str
    deficit: Decimal


def record_missing_fx_pair(diagnostics: Any, pair: str) -> None:
    if pair not in diagnostics.missing_fx_pairs:
        diagnostics.missing_fx_pairs.append(pair)
    if pair not in diagnostics.data_quality["fx_missing"]:
        diagnostics.data_quality["fx_missing"].append(pair)


def funding_priority_currencies(
    *, options: Any, base_currency: str, target_currency: str, cash_ledger: dict[str, Decimal]
) -> list[str]:
    if options.fx_funding_source_currency == "BASE_ONLY":
        if base_currency != target_currency:
            return [base_currency]
        return []

    candidates = [base_currency] if base_currency != target_currency else []
    other = sorted(c for c in cash_ledger.keys() if c not in {base_currency, target_currency})
    return candidates + other


def select_funding_source(
    *,
    after_portfolio: Any,
    market_data: Any,
    options: Any,
    diagnostics: Any,
    target_currency: str,
    fx_needed: Decimal,
    cash_ledger: dict[str, Decimal],
) -> tuple[Optional[FundingSelection], Optional[FundingDeficit]]:
    candidates = funding_priority_currencies(
        options=options,
        base_currency=after_portfolio.base_currency,
        target_currency=target_currency,
        cash_ledger=cash_ledger,
    )

    smallest_deficit: Optional[FundingDeficit] = None
    for funding_currency in candidates:
        pair = f"{target_currency}/{funding_currency}"
        rate = get_fx_rate(market_data, target_currency, funding_currency)
        if rate is None:
            record_missing_fx_pair(diagnostics, pair)
            continue

        sell_required = quantize_amount_for_currency(
            fx_needed * rate,
            funding_currency,
        )
        available_funding = ensure_cash_balance(after_portfolio, funding_currency).amount

        if available_funding >= sell_required:
            return (
                {
                    "pair": pair,
                    "rate": rate,
                    "funding_currency": funding_currency,
                    "sell_required": sell_required,
                },
                smallest_deficit,
            )

        deficit = sell_required - available_funding
        if smallest_deficit is None or deficit < smallest_deficit["deficit"]:
            smallest_deficit = {
                "currency": funding_currency,
                "deficit": deficit,
            }

    return None, smallest_deficit
