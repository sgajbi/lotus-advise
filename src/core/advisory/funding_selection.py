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


class _FundingCandidate(TypedDict):
    pair: str
    funding_currency: str
    rate: Decimal | None


def record_missing_fx_pair(diagnostics: Any, pair: str) -> None:
    if pair not in diagnostics.missing_fx_pairs:
        diagnostics.missing_fx_pairs.append(pair)
    if pair not in diagnostics.data_quality["fx_missing"]:
        diagnostics.data_quality["fx_missing"].append(pair)


def funding_priority_currencies(
    *, options: Any, base_currency: str, target_currency: str, cash_ledger: dict[str, Decimal]
) -> list[str]:
    if options.fx_funding_source_currency == "BASE_ONLY":
        return _base_only_funding_candidates(base_currency, target_currency)

    return _any_cash_funding_candidates(base_currency, target_currency, cash_ledger)


def _base_only_funding_candidates(base_currency: str, target_currency: str) -> list[str]:
    if base_currency == target_currency:
        return []
    return [base_currency]


def _any_cash_funding_candidates(
    base_currency: str,
    target_currency: str,
    cash_ledger: dict[str, Decimal],
) -> list[str]:
    candidates = _base_only_funding_candidates(base_currency, target_currency)
    candidates.extend(
        sorted(
            currency for currency in cash_ledger if currency not in {base_currency, target_currency}
        )
    )
    return candidates


def _candidate_funding_source(
    *, market_data: Any, target_currency: str, funding_currency: str
) -> _FundingCandidate:
    pair = f"{target_currency}/{funding_currency}"
    return {
        "pair": pair,
        "funding_currency": funding_currency,
        "rate": get_fx_rate(market_data, target_currency, funding_currency),
    }


def _funding_selection_for_candidate(
    *,
    after_portfolio: Any,
    fx_needed: Decimal,
    candidate: _FundingCandidate,
) -> tuple[FundingSelection | None, FundingDeficit | None]:
    funding_currency = candidate["funding_currency"]
    rate = candidate["rate"]
    if rate is None:
        raise ValueError("Funding candidate must have an FX rate before selection")

    sell_required = quantize_amount_for_currency(fx_needed * rate, funding_currency)
    available_funding = ensure_cash_balance(after_portfolio, funding_currency).amount
    if available_funding >= sell_required:
        return (
            {
                "pair": candidate["pair"],
                "rate": rate,
                "funding_currency": funding_currency,
                "sell_required": sell_required,
            },
            None,
        )

    return None, {
        "currency": funding_currency,
        "deficit": sell_required - available_funding,
    }


def _smaller_funding_deficit(
    current: FundingDeficit | None,
    candidate: FundingDeficit,
) -> FundingDeficit:
    if current is None or candidate["deficit"] < current["deficit"]:
        return candidate
    return current


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

    smallest_deficit: FundingDeficit | None = None
    for funding_currency in candidates:
        candidate = _candidate_funding_source(
            market_data=market_data,
            target_currency=target_currency,
            funding_currency=funding_currency,
        )
        if candidate["rate"] is None:
            record_missing_fx_pair(diagnostics, candidate["pair"])
            continue

        selection, deficit = _funding_selection_for_candidate(
            after_portfolio=after_portfolio,
            fx_needed=fx_needed,
            candidate=candidate,
        )
        if selection is not None:
            return selection, smallest_deficit
        if deficit is not None:
            smallest_deficit = _smaller_funding_deficit(smallest_deficit, deficit)

    return None, smallest_deficit
