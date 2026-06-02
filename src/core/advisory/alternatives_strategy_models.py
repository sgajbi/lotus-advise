from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from src.core.advisory.alternatives_models import (
    AlternativeCandidateSeed,
    RejectedAlternativeCandidate,
)


class StrategyPosition(BaseModel):
    instrument_id: str = Field(description="Held instrument identifier.")
    quantity: Decimal = Field(description="Held quantity.")
    price: Decimal | None = Field(default=None, description="Last known local price.")
    currency: str | None = Field(default=None, description="Price currency when available.")


class StrategyTradeIntent(BaseModel):
    side: Literal["BUY", "SELL"] = Field(description="Baseline proposal trade side.")
    instrument_id: str = Field(description="Instrument identifier used in the baseline trade.")
    quantity: Decimal | None = Field(default=None, description="Trade quantity when available.")
    notional_amount: Decimal | None = Field(
        default=None,
        description="Trade notional amount when quantity is not available.",
    )
    notional_currency: str | None = Field(
        default=None,
        description="Trade notional currency when notional is available.",
    )


class StrategyShelfInstrument(BaseModel):
    instrument_id: str = Field(description="Shelf-backed instrument identifier.")
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"] = Field(
        description="Current shelf posture."
    )
    asset_class: str = Field(default="UNKNOWN", description="Shelf asset class.")


class AlternativeStrategyInputs(BaseModel):
    portfolio_id: str = Field(
        description="Portfolio identifier associated with the baseline proposal."
    )
    base_currency: str = Field(description="Baseline portfolio currency.")
    positions: tuple[StrategyPosition, ...] = Field(
        default=(),
        description="Deterministic ordered positions from the baseline portfolio.",
    )
    cash_balances: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Cash balances keyed by currency.",
    )
    shelf_instruments: tuple[StrategyShelfInstrument, ...] = Field(
        default=(),
        description="Deterministic ordered shelf instruments available to the strategy.",
    )
    current_proposed_trades: tuple[StrategyTradeIntent, ...] = Field(
        default=(),
        description="Deterministic ordered baseline proposed trades.",
    )

    @property
    def held_instrument_ids(self) -> tuple[str, ...]:
        return tuple(position.instrument_id for position in self.positions)

    @property
    def shelf_instrument_ids(self) -> tuple[str, ...]:
        return tuple(instrument.instrument_id for instrument in self.shelf_instruments)

    @property
    def current_trade_instrument_ids(self) -> tuple[str, ...]:
        return tuple(trade.instrument_id for trade in self.current_proposed_trades)


class AlternativeStrategyBuildResult(BaseModel):
    seeds: tuple[AlternativeCandidateSeed, ...] = Field(default=())
    rejected_candidates: tuple[RejectedAlternativeCandidate, ...] = Field(default=())
