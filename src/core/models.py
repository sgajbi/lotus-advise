from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --- Primitives ---
class Money(BaseModel):
    amount: Decimal
    currency: str


class FxRate(BaseModel):
    pair: str
    rate: Decimal


# --- Inputs ---
class Position(BaseModel):
    instrument_id: str
    quantity: Decimal
    market_value: Optional[Money] = None


class CashBalance(BaseModel):
    currency: str
    amount: Decimal
    settled: Optional[Decimal] = None
    pending: Optional[Decimal] = None


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
    fx_rates: List[FxRate] = Field(default_factory=list)


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
    allow_restricted: bool = False
    suppress_dust_trades: bool = True
    dust_trade_threshold: Optional[Money] = None
    fx_buffer_pct: Decimal = Decimal("0.01")
    single_position_max_weight: Optional[Decimal] = None
    block_on_missing_prices: bool = True


# --- Expanded Outputs (RFC-0003 Audit Bundle) ---
class AllocationBucket(BaseModel):
    bucket: str
    weight: Decimal


class SimulatedState(BaseModel):
    total_value: Money
    allocation: List[AllocationBucket] = Field(default_factory=list)
    cash_balances: List[CashBalance] = Field(default_factory=list)


class ExcludedInstrument(BaseModel):
    instrument_id: str
    reason_code: str
    details: Optional[str] = None


class UniverseCoverage(BaseModel):
    price_coverage_pct: Decimal
    fx_coverage_pct: Decimal


class UniverseData(BaseModel):
    universe_id: str
    eligible_for_buy: List[str] = Field(default_factory=list)
    eligible_for_sell: List[str] = Field(default_factory=list)
    excluded: List[ExcludedInstrument] = Field(default_factory=list)
    coverage: UniverseCoverage


class TargetInstrument(BaseModel):
    """Tracks the transition from model-requested weight to final calculated weight[cite: 333]."""

    instrument_id: str
    model_weight: Decimal  # Requested weight from the Strategy [cite: 333]
    final_weight: Decimal  # Actual weight after Shelf/Constraint checks [cite: 333]
    final_value: Money  # Monetary value of the final weight [cite: 333]
    tags: List[str] = Field(
        default_factory=list
    )  # e.g., "CAPPED_SINGLE_POS", "SELL_ONLY_ZEROED" [cite: 333]


class TargetData(BaseModel):
    """Captures the outcome of target generation with full lineage[cite: 333]."""

    target_id: str
    strategy: Dict[str, Any]  # Strategy metadata
    targets: List[TargetInstrument]


class IntentRationale(BaseModel):
    code: str
    message: str


class OrderIntent(BaseModel):
    intent_id: str
    intent_type: Literal["SECURITY_TRADE", "FX_SPOT"] = "SECURITY_TRADE"
    side: Literal["BUY", "SELL", "BUY_BASE_SELL_QUOTE", "SELL_BASE_BUY_QUOTE"]

    # Security Fields
    instrument_id: Optional[str] = None
    quantity: Optional[Decimal] = None
    notional: Optional[Money] = None

    # FX Fields
    pair: Optional[str] = None
    buy_currency: Optional[str] = None
    buy_amount: Optional[Decimal] = None
    sell_currency: Optional[str] = None
    estimated_sell_amount: Optional[Decimal] = None

    # Metadata
    dependencies: List[str] = Field(default_factory=list)
    rationale: Optional[IntentRationale] = None


class RuleResult(BaseModel):
    rule_id: str
    severity: Literal["HARD", "SOFT"]
    status: Literal["PASS", "FAIL"]
    measured: Decimal
    threshold: Dict[str, Decimal]
    reason_code: str
    remediation_hint: Optional[str] = None


class SuppressedIntent(BaseModel):
    """Captured trades dropped due to min_notional or dust thresholds[cite: 334]."""

    instrument_id: str
    reason: str  # e.g., "BELOW_MIN_NOTIONAL" [cite: 334]
    intended_notional: Money
    threshold: Money


class DiagnosticsData(BaseModel):
    """Granular reporting of data quality and processing outcomes[cite: 334]."""

    warnings: List[str] = Field(default_factory=list)
    suppressed_intents: List[SuppressedIntent] = Field(default_factory=list)
    data_quality: Dict[
        str, List[str]
    ]  # Keys: "price_missing", "fx_missing", "shelf_missing" [cite: 334]


class LineageData(BaseModel):
    portfolio_snapshot_id: str
    market_data_snapshot_id: str
    request_hash: str


class RebalanceResult(BaseModel):
    """The complete, auditable result of a rebalance simulation[cite: 312]."""

    rebalance_run_id: str
    correlation_id: str
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    before: SimulatedState
    universe: UniverseData
    target: TargetData
    intents: List[OrderIntent]
    after_simulated: SimulatedState
    rule_results: List[RuleResult] = Field(default_factory=list)
    explanation: Dict[str, Any]
    diagnostics: DiagnosticsData
    lineage: LineageData
