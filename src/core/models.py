"""
FILE: src/core/models.py
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ValuationMode(str, Enum):
    CALCULATED = "CALCULATED"
    TRUST_SNAPSHOT = "TRUST_SNAPSHOT"


class Money(BaseModel):
    amount: Decimal
    currency: str


class FxRate(BaseModel):
    pair: str
    rate: Decimal


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
    asset_class: str = "UNKNOWN"
    min_notional: Optional[Money] = None


class EngineOptions(BaseModel):
    valuation_mode: ValuationMode = ValuationMode.CALCULATED

    cash_band_min_weight: Decimal = Decimal("0.00")
    cash_band_max_weight: Decimal = Decimal("1.00")

    single_position_max_weight: Optional[Decimal] = None
    min_trade_notional: Optional[Money] = None

    allow_restricted: bool = False
    suppress_dust_trades: bool = True
    dust_trade_threshold: Optional[Money] = None
    fx_buffer_pct: Decimal = Decimal("0.01")
    block_on_missing_prices: bool = True
    block_on_missing_fx: bool = True
    min_cash_buffer_pct: Decimal = Decimal("0.0")


class AllocationMetric(BaseModel):
    key: str
    weight: Decimal
    value: Money


class PositionSummary(BaseModel):
    instrument_id: str
    quantity: Decimal
    instrument_currency: str
    asset_class: str = "UNKNOWN"
    price: Optional[Money] = None
    value_in_instrument_ccy: Money
    value_in_base_ccy: Money
    weight: Decimal


class SimulatedState(BaseModel):
    total_value: Money
    cash_balances: List[CashBalance] = Field(default_factory=list)
    positions: List[PositionSummary] = Field(default_factory=list)
    allocation_by_asset_class: List[AllocationMetric] = Field(default_factory=list)
    allocation_by_instrument: List[AllocationMetric] = Field(default_factory=list)
    allocation: List[AllocationMetric] = Field(default_factory=list)


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
    model_config = {"protected_namespaces": ()}
    instrument_id: str
    model_weight: Decimal
    final_weight: Decimal
    final_value: Money
    tags: List[str] = Field(default_factory=list)


class TargetData(BaseModel):
    target_id: str
    strategy: Dict[str, Any]
    targets: List[TargetInstrument]


class IntentRationale(BaseModel):
    code: str
    message: str


class SecurityTradeIntent(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = "SECURITY_TRADE"
    intent_id: str
    instrument_id: str
    side: Literal["BUY", "SELL"]
    quantity: Optional[Decimal] = None
    notional: Optional[Money] = None
    notional_base: Optional[Money] = None
    dependencies: List[str] = Field(default_factory=list)
    rationale: Optional[IntentRationale] = None
    constraints_applied: List[str] = Field(default_factory=list)


class FxSpotIntent(BaseModel):
    intent_type: Literal["FX_SPOT"] = "FX_SPOT"
    intent_id: str
    pair: str
    buy_currency: str
    buy_amount: Decimal
    sell_currency: str
    sell_amount_estimated: Decimal
    dependencies: List[str] = Field(default_factory=list)
    rationale: Optional[IntentRationale] = None


OrderIntent = Union[SecurityTradeIntent, FxSpotIntent]


class RuleResult(BaseModel):
    rule_id: str
    severity: Literal["HARD", "SOFT", "INFO"]
    status: Literal["PASS", "FAIL"]
    measured: Decimal
    threshold: Dict[str, Decimal]
    reason_code: str
    remediation_hint: Optional[str] = None


class SuppressedIntent(BaseModel):
    instrument_id: str
    reason: str
    intended_notional: Money
    threshold: Money


class DiagnosticsData(BaseModel):
    warnings: List[str] = Field(default_factory=list)
    suppressed_intents: List[SuppressedIntent] = Field(default_factory=list)
    data_quality: Dict[str, List[str]]


class LineageData(BaseModel):
    portfolio_snapshot_id: str
    market_data_snapshot_id: str
    request_hash: str


class Reconciliation(BaseModel):
    before_total_value: Money
    after_total_value: Money
    delta: Money
    tolerance: Money
    status: Literal["OK", "MISMATCH"]


class RebalanceResult(BaseModel):
    """The complete, auditable result of a rebalance simulation."""

    rebalance_run_id: str
    correlation_id: str
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    before: SimulatedState
    universe: UniverseData
    target: TargetData
    intents: List[OrderIntent] = Field(discriminator="intent_type")
    after_simulated: SimulatedState
    reconciliation: Optional[Reconciliation] = None
    rule_results: List[RuleResult] = Field(default_factory=list)
    explanation: Dict[str, Any]
    diagnostics: DiagnosticsData
    lineage: LineageData
