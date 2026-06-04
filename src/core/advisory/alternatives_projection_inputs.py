from src.core.advisory.alternatives_strategies import (
    AlternativeStrategyInputs,
    StrategyPosition,
    StrategyShelfInstrument,
    StrategyTradeIntent,
)
from src.core.proposal_request_models import ProposalSimulateRequest


def build_strategy_inputs(request: ProposalSimulateRequest) -> AlternativeStrategyInputs:
    prices_by_instrument = {
        price.instrument_id: price for price in request.market_data_snapshot.prices
    }
    return AlternativeStrategyInputs(
        portfolio_id=request.portfolio_snapshot.portfolio_id,
        base_currency=request.portfolio_snapshot.base_currency,
        positions=tuple(
            StrategyPosition(
                instrument_id=position.instrument_id,
                quantity=position.quantity,
                price=(
                    prices_by_instrument[position.instrument_id].price
                    if position.instrument_id in prices_by_instrument
                    else None
                ),
                currency=(
                    prices_by_instrument[position.instrument_id].currency
                    if position.instrument_id in prices_by_instrument
                    else None
                ),
            )
            for position in request.portfolio_snapshot.positions
        ),
        cash_balances={
            balance.currency: balance.amount for balance in request.portfolio_snapshot.cash_balances
        },
        shelf_instruments=tuple(
            StrategyShelfInstrument(
                instrument_id=entry.instrument_id,
                status=entry.status,
                asset_class=entry.asset_class,
            )
            for entry in request.shelf_entries
        ),
        current_proposed_trades=tuple(
            StrategyTradeIntent(
                side=trade.side,
                instrument_id=trade.instrument_id,
                quantity=trade.quantity,
                notional_amount=(trade.notional.amount if trade.notional is not None else None),
                notional_currency=(trade.notional.currency if trade.notional is not None else None),
            )
            for trade in request.proposed_trades
        ),
    )


__all__ = ["build_strategy_inputs"]
