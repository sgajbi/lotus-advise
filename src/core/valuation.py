"""
FILE: src/core/valuation.py
"""

from decimal import Decimal
from typing import Dict, List, Optional

from src.core.models import (
    AllocationMetric,
    EngineOptions,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    PositionSummary,
    ShelfEntry,
    SimulatedState,
    ValuationMode,
)


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
    """
    Returns the FX rate to convert from_ccy -> to_ccy.
    Returns 1.0 if currencies match.
    Returns None if rate is missing.
    """
    if from_ccy == to_ccy:
        return Decimal("1.0")

    # Direct lookup
    pair = f"{from_ccy}/{to_ccy}"
    direct = next((r.rate for r in market_data.fx_rates if r.pair == pair), None)
    if direct:
        return direct

    # Inverse lookup
    pair_inv = f"{to_ccy}/{from_ccy}"
    inverse = next((r.rate for r in market_data.fx_rates if r.pair == pair_inv), None)
    if inverse:
        return Decimal("1.0") / inverse

    return None


class ValuationService:
    """
    Central authority for valuing positions and cash based on the configured mode.
    """

    @staticmethod
    def value_position(
        position: Position,
        market_data: MarketDataSnapshot,
        base_ccy: str,
        options: EngineOptions,
        dq_log: Dict[str, List[str]],
    ) -> PositionSummary:
        """
        Calculates position value based on options.valuation_mode.
        """
        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == position.instrument_id), None
        )

        # 1. Determine Unit Price & Currency
        price_val = Decimal("0")
        currency = base_ccy  # Fallback

        if price_ent:
            price_val = price_ent.price
            currency = price_ent.currency
        else:
            # DQ Logging happens in the caller (engine) usually, but we safeguard here
            # If price is missing, calculated value is 0
            pass

        # 2. Calculate Market Value (Native)
        mv_instr_ccy = Decimal("0")

        # TRUST_SNAPSHOT: Use provided MV
        is_trust = options.valuation_mode == ValuationMode.TRUST_SNAPSHOT
        if is_trust and position.market_value:
            mv_instr_ccy = position.market_value.amount
            currency = position.market_value.currency
        else:
            # CALCULATED: qty * price
            mv_instr_ccy = position.quantity * price_val

        # 3. Convert to Base
        rate = get_fx_rate(market_data, currency, base_ccy)
        if rate is None:
            # We can't value it in base currency
            mv_base = Decimal("0")
        else:
            mv_base = mv_instr_ccy * rate

        return PositionSummary(
            instrument_id=position.instrument_id,
            quantity=position.quantity,
            instrument_currency=currency,
            price=Money(amount=price_val, currency=currency) if price_ent else None,
            value_in_instrument_ccy=Money(amount=mv_instr_ccy, currency=currency),
            value_in_base_ccy=Money(amount=mv_base, currency=base_ccy),
            weight=Decimal("0"),  # Populated later by build_simulated_state
        )


def build_simulated_state(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    warnings: List[str],
    options: Optional[EngineOptions] = None,
) -> SimulatedState:
    """
    Constructs a full valuation of the portfolio.
    """
    # Default options if not provided (for backward compat in internal calls)
    if options is None:
        options = EngineOptions()

    base_ccy = portfolio.base_currency
    pos_summaries = []
    total_val = Decimal("0")

    # 1. Value Positions
    for pos in portfolio.positions:
        # Check DQ for price
        has_price = any(p.instrument_id == pos.instrument_id for p in market_data.prices)
        if not has_price:
            dq_log.setdefault("price_missing", []).append(pos.instrument_id)

        summary = ValuationService.value_position(pos, market_data, base_ccy, options, dq_log)

        # Check FX DQ
        if summary.instrument_currency != base_ccy:
            rate = get_fx_rate(market_data, summary.instrument_currency, base_ccy)
            if rate is None:
                dq_log.setdefault("fx_missing", []).append(
                    f"{summary.instrument_currency}/{base_ccy}"
                )

        pos_summaries.append(summary)
        total_val += summary.value_in_base_ccy.amount

    # 2. Value Cash
    for cash in portfolio.cash_balances:
        if cash.currency == base_ccy:
            total_val += cash.amount
        else:
            rate = get_fx_rate(market_data, cash.currency, base_ccy)
            if rate:
                total_val += cash.amount * rate
            else:
                dq_log.setdefault("fx_missing", []).append(f"{cash.currency}/{base_ccy}")

    # 3. Compute Weights
    if total_val == 0:
        total_val_safe = Decimal("1")  # Avoid Div0
    else:
        total_val_safe = total_val

    for p in pos_summaries:
        p.weight = p.value_in_base_ccy.amount / total_val_safe
        # Add Asset Class from Shelf
        shelf_entry = next((s for s in shelf if s.instrument_id == p.instrument_id), None)
        if shelf_entry:
            p.asset_class = shelf_entry.asset_class

    # 4. Aggregations
    alloc_instr = [
        AllocationMetric(key=p.instrument_id, weight=p.weight, value=p.value_in_base_ccy)
        for p in pos_summaries
    ]

    alloc_class_map = {}
    for p in pos_summaries:
        ac = p.asset_class
        alloc_class_map[ac] = alloc_class_map.get(ac, Decimal("0")) + p.value_in_base_ccy.amount

    # Add cash to allocation
    total_cash_val = Decimal("0")
    for cash in portfolio.cash_balances:
        val = cash.amount
        if cash.currency != base_ccy:
            rate = get_fx_rate(market_data, cash.currency, base_ccy)
            if rate:
                val = cash.amount * rate
            else:
                val = Decimal("0")
        total_cash_val += val

    alloc_class_map["CASH"] = alloc_class_map.get("CASH", Decimal("0")) + total_cash_val

    alloc_asset_class = [
        AllocationMetric(
            key=k,
            weight=v / total_val_safe,
            value=Money(amount=v, currency=base_ccy),
        )
        for k, v in alloc_class_map.items()
    ]

    return SimulatedState(
        total_value=Money(amount=total_val, currency=base_ccy),
        cash_balances=portfolio.cash_balances,
        positions=pos_summaries,
        allocation_by_asset_class=alloc_asset_class,
        allocation_by_instrument=alloc_instr,
        allocation=alloc_instr,  # Deprecated alias, keeping for compat
    )
