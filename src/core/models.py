"""
FILE: src/core/models.py
"""

import re
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ValuationMode(str, Enum):
    CALCULATED = "CALCULATED"
    TRUST_SNAPSHOT = "TRUST_SNAPSHOT"


class TargetMethod(str, Enum):
    HEURISTIC = "HEURISTIC"
    SOLVER = "SOLVER"


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
    lots: List["TaxLot"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_lot_quantity_total(self):
        if not self.lots:
            return self
        total = sum((lot.quantity for lot in self.lots), Decimal("0"))
        if abs(total - self.quantity) > Decimal("0.0001"):
            raise ValueError(
                "sum(lot.quantity) must equal position.quantity within tolerance 0.0001"
            )
        return self


class CashBalance(BaseModel):
    currency: str
    amount: Decimal
    settled: Optional[Decimal] = None
    pending: Optional[Decimal] = None


class PortfolioSnapshot(BaseModel):
    snapshot_id: Optional[str] = None
    portfolio_id: str
    base_currency: str
    positions: List[Position] = Field(default_factory=list)
    cash_balances: List[CashBalance] = Field(default_factory=list)


class Price(BaseModel):
    instrument_id: str
    price: Decimal
    currency: str


class MarketDataSnapshot(BaseModel):
    snapshot_id: Optional[str] = None
    prices: List[Price] = Field(default_factory=list)
    fx_rates: List[FxRate] = Field(default_factory=list)


class ModelTarget(BaseModel):
    instrument_id: str
    weight: Decimal


class ModelPortfolio(BaseModel):
    targets: List[ModelTarget]


class TaxLot(BaseModel):
    lot_id: str
    quantity: Decimal = Field(ge=0)
    unit_cost: Money
    purchase_date: str


class ShelfEntry(BaseModel):
    instrument_id: str
    status: Literal["APPROVED", "RESTRICTED", "BANNED", "SUSPENDED", "SELL_ONLY"]
    asset_class: str = "UNKNOWN"
    settlement_days: int = Field(default=2, ge=0, le=10)
    min_notional: Optional[Money] = None
    attributes: Dict[str, str] = Field(default_factory=dict)


class GroupConstraint(BaseModel):
    max_weight: Decimal

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v: Decimal) -> Decimal:
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("max_weight must be between 0 and 1 inclusive")
        return v


class EngineOptions(BaseModel):
    valuation_mode: ValuationMode = ValuationMode.CALCULATED
    target_method: TargetMethod = TargetMethod.HEURISTIC
    compare_target_methods: bool = False
    compare_target_methods_tolerance: Decimal = Decimal("0.0001")

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
    max_turnover_pct: Optional[Decimal] = None
    enable_tax_awareness: bool = False
    max_realized_capital_gains: Optional[Decimal] = Field(default=None, ge=0)
    enable_settlement_awareness: bool = False
    settlement_horizon_days: int = Field(default=5, ge=0, le=10)
    fx_settlement_days: int = Field(default=2, ge=0, le=10)
    max_overdraft_by_ccy: Dict[str, Decimal] = Field(default_factory=dict)

    # Key format: "<attribute_key>:<attribute_value>", for example "sector:TECH"
    group_constraints: Dict[str, GroupConstraint] = Field(default_factory=dict)

    @field_validator("group_constraints")
    @classmethod
    def validate_group_constraint_keys(
        cls, v: Dict[str, GroupConstraint]
    ) -> Dict[str, GroupConstraint]:
        for key in v:
            if key.count(":") != 1:
                raise ValueError(
                    "group_constraints keys must use format '<attribute_key>:<attribute_value>'"
                )
            attr_key, attr_val = key.split(":", 1)
            if not attr_key or not attr_val:
                raise ValueError(
                    "group_constraints keys must use format '<attribute_key>:<attribute_value>'"
                )
        return v

    @field_validator("max_turnover_pct")
    @classmethod
    def validate_max_turnover_pct(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is None:
            return v
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("max_turnover_pct must be between 0 and 1 inclusive")
        return v

    @field_validator("max_overdraft_by_ccy")
    @classmethod
    def validate_max_overdraft_by_ccy(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        for ccy, amount in v.items():
            if not ccy:
                raise ValueError("max_overdraft_by_ccy keys must be non-empty currency codes")
            if amount < Decimal("0"):
                raise ValueError("max_overdraft_by_ccy values must be non-negative")
        return v


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
    allocation_by_attribute: Dict[str, List[AllocationMetric]] = Field(default_factory=dict)


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


class DroppedIntent(BaseModel):
    instrument_id: str
    reason: str
    potential_notional: Money
    score: Decimal


class GroupConstraintEvent(BaseModel):
    constraint_key: str
    group_weight_before: Decimal
    max_weight: Decimal
    released_weight: Decimal
    recipients: Dict[str, Decimal] = Field(default_factory=dict)
    status: Literal["CAPPED", "BLOCKED"]


class TaxBudgetConstraintEvent(BaseModel):
    instrument_id: str
    requested_quantity: Decimal
    allowed_quantity: Decimal
    reason_code: str


class CashLadderPoint(BaseModel):
    date_offset: int
    currency: str
    projected_balance: Decimal


class CashLadderBreach(BaseModel):
    date_offset: int
    currency: str
    projected_balance: Decimal
    allowed_floor: Decimal
    reason_code: str


class DiagnosticsData(BaseModel):
    warnings: List[str] = Field(default_factory=list)
    suppressed_intents: List[SuppressedIntent] = Field(default_factory=list)
    dropped_intents: List[DroppedIntent] = Field(default_factory=list)
    group_constraint_events: List[GroupConstraintEvent] = Field(default_factory=list)
    tax_budget_constraint_events: List[TaxBudgetConstraintEvent] = Field(default_factory=list)
    cash_ladder: List[CashLadderPoint] = Field(default_factory=list)
    cash_ladder_breaches: List[CashLadderBreach] = Field(default_factory=list)
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


class TaxImpact(BaseModel):
    total_realized_gain: Money
    total_realized_loss: Money
    budget_limit: Optional[Money] = None
    budget_used: Optional[Money] = None


class RebalanceResult(BaseModel):
    """The complete, auditable result of a rebalance simulation."""

    rebalance_run_id: str
    correlation_id: str
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    before: SimulatedState
    universe: UniverseData
    target: TargetData
    intents: List[Annotated[OrderIntent, Field(discriminator="intent_type")]]
    after_simulated: SimulatedState
    reconciliation: Optional[Reconciliation] = None
    tax_impact: Optional[TaxImpact] = None
    rule_results: List[RuleResult] = Field(default_factory=list)
    explanation: Dict[str, Any]
    diagnostics: DiagnosticsData
    lineage: LineageData


class SimulationScenario(BaseModel):
    description: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class BatchRebalanceRequest(BaseModel):
    MAX_SCENARIOS_PER_REQUEST: ClassVar[int] = 20

    portfolio_snapshot: PortfolioSnapshot
    market_data_snapshot: MarketDataSnapshot
    model_portfolio: ModelPortfolio
    shelf_entries: List[ShelfEntry]
    scenarios: Dict[str, SimulationScenario]

    @field_validator("scenarios")
    @classmethod
    def validate_scenarios(
        cls, scenarios: Dict[str, SimulationScenario]
    ) -> Dict[str, SimulationScenario]:
        if not scenarios:
            raise ValueError("at least one scenario is required")
        if len(scenarios) > cls.MAX_SCENARIOS_PER_REQUEST:
            raise ValueError(f"scenario count exceeds maximum of {cls.MAX_SCENARIOS_PER_REQUEST}")

        pattern = re.compile(r"^[a-z0-9_-]{1,64}$")
        seen_normalized = set()
        for scenario_name in scenarios:
            if not pattern.fullmatch(scenario_name):
                raise ValueError("scenario names must match regex [a-z0-9_\\-]{1,64}")
            normalized = scenario_name.lower()
            if normalized in seen_normalized:
                raise ValueError("duplicate scenario keys after case normalization")
            seen_normalized.add(normalized)

        return scenarios


class BatchScenarioMetric(BaseModel):
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"]
    security_intent_count: int
    gross_turnover_notional_base: Money


class BatchRebalanceResult(BaseModel):
    batch_run_id: str
    run_at_utc: str
    base_snapshot_ids: Dict[str, str]
    results: Dict[str, RebalanceResult] = Field(default_factory=dict)
    comparison_metrics: Dict[str, BatchScenarioMetric] = Field(default_factory=dict)
    failed_scenarios: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
