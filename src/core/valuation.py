"""
FILE: src/core/valuation.py
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, cast

from src.core.engine_options_models import EngineOptions, ValuationMode
from src.core.portfolio_models import (
    CashBalance,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    Price,
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

    direct_rate = _fx_rate_for_pair(market_data, _fx_pair(from_ccy, to_ccy))
    if direct_rate:
        return _decimal_fx_rate(direct_rate)

    inverse_rate = _fx_rate_for_pair(market_data, _fx_pair(to_ccy, from_ccy))
    if inverse_rate:
        return Decimal("1.0") / _decimal_fx_rate(inverse_rate)

    return None


def _fx_pair(from_ccy: str, to_ccy: str) -> str:
    return f"{from_ccy}/{to_ccy}"


def _fx_rate_for_pair(market_data: MarketDataSnapshot, pair: str) -> Optional[Decimal]:
    return next((rate.rate for rate in market_data.fx_rates if rate.pair == pair), None)


def _decimal_fx_rate(rate: Decimal) -> Decimal:
    return Decimal(str(rate))


@dataclass(frozen=True)
class _PositionValuation:
    price_entry: Optional[Price]
    price_value: Decimal
    currency: str
    instrument_value: Decimal
    base_value: Decimal


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
        valuation = _value_position_amounts(
            position,
            market_data,
            base_ccy,
            options,
        )

        return PositionSummary(
            instrument_id=position.instrument_id,
            quantity=position.quantity,
            instrument_currency=valuation.currency,
            price=(
                Money(amount=valuation.price_value, currency=valuation.currency)
                if valuation.price_entry
                else None
            ),
            value_in_instrument_ccy=Money(
                amount=valuation.instrument_value,
                currency=valuation.currency,
            ),
            value_in_base_ccy=Money(amount=valuation.base_value, currency=base_ccy),
            weight=Decimal("0"),
        )


def _value_position_amounts(
    position: Position,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    options: EngineOptions,
) -> _PositionValuation:
    price_entry = _price_for_position(position, market_data)
    price_value = price_entry.price if price_entry else Decimal("0")

    if options.valuation_mode == ValuationMode.TRUST_SNAPSHOT and position.market_value:
        return _trust_snapshot_position_value(
            position,
            market_data,
            base_ccy,
            price_entry,
            price_value,
        )

    return _mark_to_market_position_value(
        position,
        market_data,
        base_ccy,
        price_entry,
        price_value,
    )


def _price_for_position(
    position: Position,
    market_data: MarketDataSnapshot,
) -> Optional[Price]:
    return next(
        (price for price in market_data.prices if price.instrument_id == position.instrument_id),
        None,
    )


def _trust_snapshot_position_value(
    position: Position,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    price_entry: Optional[Price],
    price_value: Decimal,
) -> _PositionValuation:
    trusted_value = position.market_value
    if trusted_value is None:
        return _mark_to_market_position_value(
            position,
            market_data,
            base_ccy,
            price_entry,
            price_value,
        )

    price_currency = price_entry.currency if price_entry is not None else trusted_value.currency
    if _trust_snapshot_uses_base_authority(trusted_value, price_currency, base_ccy):
        return _PositionValuation(
            price_entry=price_entry,
            price_value=price_value,
            currency=price_currency,
            instrument_value=position.quantity * price_value if price_entry else Decimal("0"),
            base_value=trusted_value.amount,
        )

    return _PositionValuation(
        price_entry=price_entry,
        price_value=price_value,
        currency=trusted_value.currency,
        instrument_value=trusted_value.amount,
        base_value=_converted_base_value(
            trusted_value.amount,
            trusted_value.currency,
            base_ccy,
            market_data,
        ),
    )


def _trust_snapshot_uses_base_authority(
    trusted_value: Money,
    price_currency: str,
    base_ccy: str,
) -> bool:
    return trusted_value.currency == base_ccy and price_currency != base_ccy


def _mark_to_market_position_value(
    position: Position,
    market_data: MarketDataSnapshot,
    base_ccy: str,
    price_entry: Optional[Price],
    price_value: Decimal,
) -> _PositionValuation:
    currency = price_entry.currency if price_entry is not None else base_ccy
    instrument_value = position.quantity * price_value
    return _PositionValuation(
        price_entry=price_entry,
        price_value=price_value,
        currency=currency,
        instrument_value=instrument_value,
        base_value=_converted_base_value(instrument_value, currency, base_ccy, market_data),
    )


def _converted_base_value(
    amount: Decimal,
    currency: str,
    base_ccy: str,
    market_data: MarketDataSnapshot,
) -> Decimal:
    rate = get_fx_rate(market_data, currency, base_ccy)
    if rate is None:
        return Decimal("0")
    return amount * rate


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
    amount = cast(Decimal, cash.amount)
    if cash.currency == base_ccy:
        return amount

    rate = get_fx_rate(market_data, cash.currency, base_ccy)
    if rate:
        return amount * rate

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
