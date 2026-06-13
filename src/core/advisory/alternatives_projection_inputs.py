from decimal import Decimal

from src.core.advisory.alternatives_strategies import (
    AlternativeStrategyInputs,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
)
from src.core.portfolio_models import (
    CashBalance,
    Position,
    Price,
    ShelfEntry,
)
from src.core.proposal_request_models import ProposalSimulateRequest, ProposedTrade


def build_strategy_inputs(request: ProposalSimulateRequest) -> AlternativeStrategyInputs:
    prices_by_instrument = price_by_instrument(request.market_data_snapshot.prices)
    return AlternativeStrategyInputs(
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        base_currency=request.portfolio_snapshot.base_currency,
        positions=build_strategy_positions(
            positions=request.portfolio_snapshot.positions,
            prices_by_instrument=prices_by_instrument,
        ),
        cash_balances=build_strategy_cash_balances(request.portfolio_snapshot.cash_balances),
        shelf_instruments=build_strategy_shelf_instruments(request.shelf_entries),
        current_proposed_trades=build_strategy_trade_intents(request.proposed_trades),
    )


def price_by_instrument(prices: list[Price]) -> dict[str, Price]:
    return {price.instrument_id: price for price in prices}


def build_strategy_positions(
    *,
    positions: list[Position],
    prices_by_instrument: dict[str, Price],
) -> tuple[StrategyPosition, ...]:
    return tuple(
        strategy_position(position=position, price=prices_by_instrument.get(position.instrument_id))
        for position in positions
    )


def strategy_position(*, position: Position, price: Price | None) -> StrategyPosition:
    return StrategyPosition(
        instrument_id=position.instrument_id,
        quantity=position.quantity,
        price=(price.price if price is not None else None),
        currency=(price.currency if price is not None else None),
    )


def build_strategy_cash_balances(balances: list[CashBalance]) -> dict[str, Decimal]:
    return {balance.currency: balance.amount for balance in balances}


def build_strategy_shelf_instruments(
    entries: list[ShelfEntry],
) -> tuple[StrategyShelfInstrument, ...]:
    return tuple(
        StrategyShelfInstrument(
            instrument_id=entry.instrument_id,
            status=entry.status,
            asset_class=entry.asset_class,
        )
        for entry in entries
    )


def build_strategy_trade_intents(
    trades: list[ProposedTrade],
) -> tuple[StrategyTradeIntent, ...]:
    return tuple(strategy_trade_intent(trade) for trade in trades)


def strategy_trade_intent(trade: ProposedTrade) -> StrategyTradeIntent:
    return StrategyTradeIntent(
        side=trade.side,
        instrument_id=trade.instrument_id,
        quantity=trade.quantity,
        notional_amount=(trade.notional.amount if trade.notional is not None else None),
        notional_currency=(trade.notional.currency if trade.notional is not None else None),
    )


__all__ = [
    "build_strategy_cash_balances",
    "build_strategy_inputs",
    "build_strategy_positions",
    "build_strategy_shelf_instruments",
    "build_strategy_trade_intents",
    "price_by_instrument",
    "strategy_position",
    "strategy_trade_intent",
]
