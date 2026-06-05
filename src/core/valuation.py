"""
FILE: src/core/valuation.py
"""

from decimal import Decimal
from typing import Dict, List, Optional

from src.core.engine_options_models import EngineOptions, ValuationMode
from src.core.portfolio_models import (
    CashBalance,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    ShelfEntry,
)
from src.core.simulation_state_models import AllocationMetric, PositionSummary, SimulatedState


def get_fx_rate(market_data: MarketDataSnapshot, from_ccy: str, to_ccy: str) -> Optional[Decimal]:
    """
    Returns the FX rate to convert from_ccy -> to_ccy.
    Returns 1.0 if currencies match.
    Returns None if rate is missing.
    """
    if from_ccy == to_ccy:
        return Decimal("1.0")

    pair = f"{from_ccy}/{to_ccy}"
    direct = next((r.rate for r in market_data.fx_rates if r.pair == pair), None)
    if direct:
        return Decimal(str(direct))

    pair_inv = f"{to_ccy}/{from_ccy}"
    inverse = next((r.rate for r in market_data.fx_rates if r.pair == pair_inv), None)
    if inverse:
        return Decimal("1.0") / Decimal(str(inverse))

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

        price_val = Decimal("0")
        currency = base_ccy

        if price_ent:
            price_val = price_ent.price
            currency = price_ent.currency

        mv_instr_ccy = Decimal("0")

        is_trust = options.valuation_mode == ValuationMode.TRUST_SNAPSHOT
        if is_trust and position.market_value:
            trusted_value = position.market_value
            price_currency = price_ent.currency if price_ent is not None else trusted_value.currency
            trust_is_base_authority = (
                trusted_value.currency == base_ccy and price_currency != base_ccy
            )
            if trust_is_base_authority:
                currency = price_currency
                mv_instr_ccy = (
                    position.quantity * price_val if price_ent is not None else Decimal("0")
                )
                mv_base = trusted_value.amount
            else:
                mv_instr_ccy = trusted_value.amount
                currency = trusted_value.currency
                rate = get_fx_rate(market_data, currency, base_ccy)
                if rate is None:
                    mv_base = Decimal("0")
                else:
                    mv_base = mv_instr_ccy * rate
        else:
            mv_instr_ccy = position.quantity * price_val
            rate = get_fx_rate(market_data, currency, base_ccy)
            if rate is None:
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
            weight=Decimal("0"),
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
    if options is None:
        options = EngineOptions()

    base_ccy = portfolio.base_currency
    pos_summaries, position_total = _build_position_summaries(
        portfolio.positions,
        market_data,
        base_ccy,
        options,
        dq_log,
    )
    total_cash_val = _cash_total_value(portfolio.cash_balances, market_data, base_ccy, dq_log)
    total_val = position_total + total_cash_val
    total_val_safe = _safe_total_value(total_val)

    alloc_class_map, alloc_attr_map = _build_position_allocation_maps(
        pos_summaries,
        _shelf_by_instrument(shelf),
        total_val_safe,
    )
    _add_cash_allocation(alloc_class_map, total_cash_val)

    alloc_instr = _instrument_allocations(pos_summaries)
    alloc_asset_class = _allocation_metrics(alloc_class_map, total_val_safe, base_ccy)
    alloc_by_attr = _attribute_allocation_metrics(alloc_attr_map, total_val_safe, base_ccy)

    return SimulatedState(
        total_value=Money(amount=total_val, currency=base_ccy),
        cash_balances=portfolio.cash_balances,
        positions=pos_summaries,
        allocation_by_asset_class=alloc_asset_class,
        allocation_by_instrument=alloc_instr,
        allocation=alloc_instr,
        allocation_by_attribute=alloc_by_attr,
    )


def _build_position_summaries(
    positions: List[Position],
    market_data: MarketDataSnapshot,
    base_ccy: str,
    options: EngineOptions,
    dq_log: Dict[str, List[str]],
) -> tuple[List[PositionSummary], Decimal]:
    summaries: List[PositionSummary] = []
    total_value = Decimal("0")

    for position in positions:
        _record_missing_price(position, market_data, dq_log)
        summary = ValuationService.value_position(position, market_data, base_ccy, options, dq_log)
        _record_missing_position_fx(summary, market_data, base_ccy, dq_log)
        summaries.append(summary)
        total_value += summary.value_in_base_ccy.amount

    return summaries, total_value


def _record_missing_price(
    position: Position,
    market_data: MarketDataSnapshot,
    dq_log: Dict[str, List[str]],
) -> None:
    has_price = any(price.instrument_id == position.instrument_id for price in market_data.prices)
    if not has_price:
        dq_log.setdefault("price_missing", []).append(position.instrument_id)


def _record_missing_position_fx(
    summary: PositionSummary,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    dq_log: Dict[str, List[str]],
) -> None:
    if summary.instrument_currency == base_ccy:
        return

    rate = get_fx_rate(market_data, summary.instrument_currency, base_ccy)
    if rate is None:
        dq_log.setdefault("fx_missing", []).append(f"{summary.instrument_currency}/{base_ccy}")


def _cash_total_value(
    cash_balances: List[CashBalance],
    market_data: MarketDataSnapshot,
    base_ccy: str,
    dq_log: Dict[str, List[str]],
) -> Decimal:
    return sum(
        (_cash_value_in_base(cash, market_data, base_ccy, dq_log) for cash in cash_balances),
        Decimal("0"),
    )


def _cash_value_in_base(
    cash: CashBalance,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    dq_log: Dict[str, List[str]],
) -> Decimal:
    if cash.currency == base_ccy:
        return cash.amount

    rate = get_fx_rate(market_data, cash.currency, base_ccy)
    if rate:
        return cash.amount * rate

    dq_log.setdefault("fx_missing", []).append(f"{cash.currency}/{base_ccy}")
    return Decimal("0")


def _safe_total_value(total_value: Decimal) -> Decimal:
    if total_value == 0:
        return Decimal("1")
    return total_value


def _shelf_by_instrument(shelf: List[ShelfEntry]) -> Dict[str, ShelfEntry]:
    entries: Dict[str, ShelfEntry] = {}
    for shelf_entry in shelf:
        entries.setdefault(shelf_entry.instrument_id, shelf_entry)
    return entries


def _build_position_allocation_maps(
    positions: List[PositionSummary],
    shelf_entries: Dict[str, ShelfEntry],
    total_val_safe: Decimal,
) -> tuple[Dict[str, Decimal], Dict[str, Dict[str, Decimal]]]:
    alloc_class_map: Dict[str, Decimal] = {}
    alloc_attr_map: Dict[str, Dict[str, Decimal]] = {}

    for position in positions:
        position.weight = position.value_in_base_ccy.amount / total_val_safe
        _apply_shelf_allocation_attributes(position, shelf_entries, alloc_attr_map)
        alloc_class_map[position.asset_class] = (
            alloc_class_map.get(position.asset_class, Decimal("0"))
            + position.value_in_base_ccy.amount
        )

    return alloc_class_map, alloc_attr_map


def _apply_shelf_allocation_attributes(
    position: PositionSummary,
    shelf_entries: Dict[str, ShelfEntry],
    alloc_attr_map: Dict[str, Dict[str, Decimal]],
) -> None:
    shelf_entry = shelf_entries.get(position.instrument_id)
    if shelf_entry is None:
        return

    position.asset_class = shelf_entry.asset_class
    for attr_key, attr_val in shelf_entry.attributes.items():
        attr_allocations = alloc_attr_map.setdefault(attr_key, {})
        attr_allocations[attr_val] = (
            attr_allocations.get(attr_val, Decimal("0")) + position.value_in_base_ccy.amount
        )


def _add_cash_allocation(alloc_class_map: Dict[str, Decimal], total_cash_val: Decimal) -> None:
    alloc_class_map["CASH"] = alloc_class_map.get("CASH", Decimal("0")) + total_cash_val


def _instrument_allocations(positions: List[PositionSummary]) -> List[AllocationMetric]:
    return [
        AllocationMetric(
            key=position.instrument_id,
            weight=position.weight,
            value=position.value_in_base_ccy,
        )
        for position in positions
    ]


def _allocation_metrics(
    allocation_map: Dict[str, Decimal],
    total_val_safe: Decimal,
    base_ccy: str,
) -> List[AllocationMetric]:
    return [
        AllocationMetric(
            key=key,
            weight=value / total_val_safe,
            value=Money(amount=value, currency=base_ccy),
        )
        for key, value in allocation_map.items()
    ]


def _attribute_allocation_metrics(
    alloc_attr_map: Dict[str, Dict[str, Decimal]],
    total_val_safe: Decimal,
    base_ccy: str,
) -> Dict[str, List[AllocationMetric]]:
    return {
        attr_key: _allocation_metrics(val_map, total_val_safe, base_ccy)
        for attr_key, val_map in alloc_attr_map.items()
    }
