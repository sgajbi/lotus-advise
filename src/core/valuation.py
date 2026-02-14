"""
FILE: src/core/valuation.py
Domain logic for valuing portfolios and normalizing currency.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.core.models import (
    AllocationMetric,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    PositionSummary,
    ShelfEntry,
    SimulatedState,
)


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
    """Retrieves FX rate from snapshot, handles identity case."""
    if from_ccy == to_ccy:
        return Decimal("1.0")
    pair_name = f"{from_ccy}/{to_ccy}"
    rate_entry = next((fx for fx in market_data.fx_rates if fx.pair == pair_name), None)
    return rate_entry.rate if rate_entry else None


def evaluate_portfolio_state(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    diagnostics_warnings: List[str],
) -> Tuple[Decimal, SimulatedState]:
    """
    Computes total value and enriched state for before/after snapshots.
    Enforces the 'Currency Truth' model (Base Currency).
    """
    total_value_base = Decimal("0.0")
    positions_summary: List[PositionSummary] = []
    allocation_by_asset: Dict[str, Decimal] = {}
    allocation_by_instr: Dict[str, Decimal] = {}

    # 1. Cash Valuation
    for cash in portfolio.cash_balances:
        rate = get_fx_rate(market_data, cash.currency, portfolio.base_currency)
        if rate is None:
            if cash.amount != 0:
                dq_log.setdefault("fx_missing", []).append(
                    f"{cash.currency}/{portfolio.base_currency}"
                )
        else:
            val_base = cash.amount * rate
            total_value_base += val_base
            allocation_by_asset["CASH"] = allocation_by_asset.get("CASH", Decimal("0")) + val_base

    # 2. Position Valuation
    for pos in portfolio.positions:
        if pos.quantity == 0:
            continue

        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == pos.instrument_id), None
        )
        if not price_ent:
            dq_log.setdefault("price_missing", []).append(pos.instrument_id)
            continue

        rate = get_fx_rate(market_data, price_ent.currency, portfolio.base_currency)
        if rate is None:
            dq_log.setdefault("fx_missing", []).append(
                f"{price_ent.currency}/{portfolio.base_currency}"
            )
            continue

        comp_instr = pos.quantity * price_ent.price
        comp_base = comp_instr * rate
        final_val_base = comp_base

        # Cross-check with upstream Market Value if provided
        if pos.market_value and pos.market_value.currency == portfolio.base_currency:
            if comp_base != 0 and (abs(pos.market_value.amount - comp_base) / comp_base) > Decimal(
                "0.005"
            ):
                diagnostics_warnings.append(f"POSITION_VALUE_MISMATCH: {pos.instrument_id}")
            final_val_base = pos.market_value.amount

        total_value_base += final_val_base
        shelf_ent = next((s for s in shelf if s.instrument_id == pos.instrument_id), None)
        asset_class = shelf_ent.asset_class if shelf_ent else "UNKNOWN"

        allocation_by_asset[asset_class] = (
            allocation_by_asset.get(asset_class, Decimal("0")) + final_val_base
        )
        allocation_by_instr[pos.instrument_id] = (
            allocation_by_instr.get(pos.instrument_id, Decimal("0")) + final_val_base
        )

        positions_summary.append(
            PositionSummary(
                instrument_id=pos.instrument_id,
                quantity=pos.quantity,
                instrument_currency=price_ent.currency,
                price=Money(amount=price_ent.price, currency=price_ent.currency),
                value_in_instrument_ccy=Money(amount=comp_instr, currency=price_ent.currency),
                value_in_base_ccy=Money(amount=final_val_base, currency=portfolio.base_currency),
                weight=Decimal("0"),
            )
        )

    # 3. Final Weight Calculation
    tv_divisor = total_value_base if total_value_base != 0 else Decimal("1")
    for p in positions_summary:
        p.weight = p.value_in_base_ccy.amount / tv_divisor

    sim_state = SimulatedState(
        total_value=Money(amount=total_value_base, currency=portfolio.base_currency),
        cash_balances=portfolio.cash_balances,
        positions=positions_summary,
        allocation_by_asset_class=[
            AllocationMetric(
                key=k,
                weight=v / tv_divisor,
                value=Money(amount=v, currency=portfolio.base_currency),
            )
            for k, v in allocation_by_asset.items()
        ],
        allocation_by_instrument=[
            AllocationMetric(
                key=k,
                weight=v / tv_divisor,
                value=Money(amount=v, currency=portfolio.base_currency),
            )
            for k, v in allocation_by_instr.items()
        ],
        allocation=[
            AllocationMetric(
                key=k,
                weight=v / tv_divisor,
                value=Money(amount=v, currency=portfolio.base_currency),
            )
            for k, v in allocation_by_asset.items()
        ],
    )
    return total_value_base, sim_state
