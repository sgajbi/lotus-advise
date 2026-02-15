"""
FILE: src/core/valuation.py
Domain logic for valuing portfolios and normalizing currency.
"""

from decimal import Decimal
from typing import Dict, List, Optional

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


def build_simulated_state(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: List[ShelfEntry],
    dq_log: Dict[str, List[str]],
    diagnostics_warnings: List[str],
) -> SimulatedState:
    """
    Computes total value and enriched state for before/after snapshots.
    Enforces the 'Currency Truth' model (Base Currency).
    RFC-0006A: Includes negative quantities in valuation; does not filter them.
    """
    total_value_base = Decimal("0.0")
    positions_summary: List[PositionSummary] = []
    allocation_by_asset: Dict[str, Decimal] = {}
    allocation_by_instr: Dict[str, Decimal] = {}

    # 1. Cash Valuation
    for cash in portfolio.cash_balances:
        # RFC-0006A: Even negative cash (if allowed) should be valued
        if cash.amount == 0 and not cash.currency == portfolio.base_currency:
            # Skip pure zero records to keep noise down, unless it's base ccy placeholder
            pass

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
        # RFC-0006A: Do not skip negative quantities. Only skip exact zero if desired,
        # but typically keeping zero helps show "Sold Out" state.
        # We will skip only if strictly 0 to reduce noise, unless it's critical.
        if pos.quantity == 0:
            continue

        price_ent = next(
            (p for p in market_data.prices if p.instrument_id == pos.instrument_id), None
        )
        if not price_ent:
            dq_log.setdefault("price_missing", []).append(pos.instrument_id)
            # Cannot value without price. Skip adding to total, log DQ.
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

        # Cross-check with upstream Market Value if provided (Only for Before state generally)
        # We only do this check if the provided market_value is in base currency for simplicity
        if pos.market_value and pos.market_value.currency == portfolio.base_currency:
            # Only warn if the difference is significant (>0.5%)
            if comp_base != 0 and (
                abs(pos.market_value.amount - comp_base) / abs(comp_base)
            ) > Decimal("0.005"):
                diagnostics_warnings.append(f"POSITION_VALUE_MISMATCH: {pos.instrument_id}")
            # RFC-0006A: Trust the calculated value for consistency in simulation,
            # or trust the snapshot?
            # RFC-0002/5 said "Trust Snapshot".
            # However, if we trust snapshot for 'Before' but calculate 'After',
            # we induce reconciliation errors due to price/fx diffs.
            # To ensure strict Before/After reconciliation (RFC-0006A),
            # we should prefer the CALCULATED value using the provided MarketData
            # unless we explicitly want to respect the source of truth.
            # Decision: Use CALCULATED value to ensure mathematical consistency with After State.
            # The mismatch warning preserves auditability.
            final_val_base = comp_base

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
                asset_class=asset_class,
                price=Money(amount=price_ent.price, currency=price_ent.currency),
                value_in_instrument_ccy=Money(amount=comp_instr, currency=price_ent.currency),
                value_in_base_ccy=Money(amount=final_val_base, currency=portfolio.base_currency),
                weight=Decimal("0"),  # Calculated below
            )
        )

    # 3. Final Weight Calculation
    # Avoid division by zero
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
    return sim_state
