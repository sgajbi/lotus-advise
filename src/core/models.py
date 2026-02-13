from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Money(BaseModel):
    amount: Decimal
    currency: str

class Position(BaseModel):
    instrument_id: str
    quantity: Decimal
    market_value: Optional[Money] = None

class CashBalance(BaseModel):
    currency: str
    amount: Decimal

class PortfolioSnapshot(BaseModel):
    portfolio_id: str
    base_currency: str
    positions: List[Position] = Field(default_factory=list)
    cash_balances: List[CashBalance] = Field(default_factory=list)

class Price(BaseModel):
    instrument_id: str
    price: Decimal
    currency: str

class MarketDataSnapshot(BaseModel):
    prices: List[Price] = Field(default_factory=list)
    fx_rates: list = Field(default_factory=list)

class ModelTarget(BaseModel):
    instrument_id: str
    weight: Decimal

class ModelPortfolio(BaseModel):
    targets: List[ModelTarget]

class ShelfEntry(BaseModel):
    instrument_id: str
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    min_notional: Optional[Money] = None

class EngineOptions(BaseModel):
    suppress_dust_trades: bool = True
    fx_buffer_pct: Decimal = Decimal("0.01")
    single_position_max_weight: Optional[Decimal] = None  # Added for constraint capping

class OrderIntent(BaseModel):
    action: Literal["BUY", "SELL", "FX_BUY", "FX_SELL"]
    instrument_id: Optional[str] = None
    quantity: Optional[Decimal] = None
    est_notional: Money

class RebalanceResult(BaseModel):
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    intents: List[OrderIntent]