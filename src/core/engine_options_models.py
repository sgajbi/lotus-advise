from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.portfolio_models import Money


class ValuationMode(str, Enum):
    CALCULATED = "CALCULATED"
    TRUST_SNAPSHOT = "TRUST_SNAPSHOT"


class TargetMethod(str, Enum):
    HEURISTIC = "HEURISTIC"
    SOLVER = "SOLVER"


_GROUP_CONSTRAINT_KEY_FORMAT = "<attribute_key>:<attribute_value>"


def _validate_group_constraint_keys(
    group_constraints: Dict[str, "GroupConstraint"],
) -> Dict[str, "GroupConstraint"]:
    for key in group_constraints:
        if key.count(":") != 1:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
        attribute_key, attribute_value = key.split(":", 1)
        if not attribute_key or not attribute_value:
            raise ValueError(
                f"group_constraints keys must use format '{_GROUP_CONSTRAINT_KEY_FORMAT}'"
            )
    return group_constraints


def _validate_optional_ratio_between_zero_and_one(
    value: Optional[Decimal], *, field_name: str
) -> Optional[Decimal]:
    if value is None:
        return value
    if value < Decimal("0") or value > Decimal("1"):
        raise ValueError(f"{field_name} must be between 0 and 1 inclusive")
    return value


def _validate_non_negative_amounts_by_currency(
    amounts_by_currency: Dict[str, Decimal], *, field_name: str
) -> Dict[str, Decimal]:
    for currency, amount in amounts_by_currency.items():
        if not currency:
            raise ValueError(f"{field_name} keys must be non-empty currency codes")
        if amount < Decimal("0"):
            raise ValueError(f"{field_name} values must be non-negative")
    return amounts_by_currency


class GroupConstraint(BaseModel):
    max_weight: Decimal = Field(
        description="Maximum allowed aggregate weight for the tagged group."
    )

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v: Decimal) -> Decimal:
        if v < Decimal("0") or v > Decimal("1"):
            raise ValueError("max_weight must be between 0 and 1 inclusive")
        return v


class SuitabilityThresholds(BaseModel):
    single_position_max_weight: Decimal = Field(
        default=Decimal("0.10"),
        ge=0,
        le=1,
        description="Maximum advisory suitability weight per single instrument.",
        examples=["0.10"],
    )
    issuer_max_weight: Decimal = Field(
        default=Decimal("0.20"),
        ge=0,
        le=1,
        description="Maximum advisory suitability aggregate weight per issuer.",
        examples=["0.20"],
    )
    max_weight_by_liquidity_tier: Dict[str, Decimal] = Field(
        default_factory=lambda: {"L4": Decimal("0.10"), "L5": Decimal("0.05")},
        description=(
            "Maximum advisory suitability aggregate weight by liquidity tier, "
            "for example {'L4': '0.10', 'L5': '0.05'}."
        ),
        examples=[{"L4": "0.10", "L5": "0.05"}],
    )
    cash_band_min_weight: Decimal = Field(
        default=Decimal("0.01"),
        ge=0,
        le=1,
        description="Minimum advisory suitability cash weight.",
        examples=["0.01"],
    )
    cash_band_max_weight: Decimal = Field(
        default=Decimal("0.05"),
        ge=0,
        le=1,
        description="Maximum advisory suitability cash weight.",
        examples=["0.05"],
    )
    data_quality_issue_severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="MEDIUM",
        description="Severity used for suitability data-quality issues.",
        examples=["MEDIUM"],
    )

    @field_validator("max_weight_by_liquidity_tier")
    @classmethod
    def validate_max_weight_by_liquidity_tier(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        for tier, value in v.items():
            if tier not in {"L1", "L2", "L3", "L4", "L5"}:
                raise ValueError("liquidity tier keys must be one of L1, L2, L3, L4, L5")
            if value < Decimal("0") or value > Decimal("1"):
                raise ValueError("liquidity-tier max weights must be between 0 and 1 inclusive")
        return v

    @model_validator(mode="after")
    def validate_cash_band(self) -> "SuitabilityThresholds":
        if self.cash_band_min_weight > self.cash_band_max_weight:
            raise ValueError("suitability cash band min cannot exceed max")
        return self


class EngineOptions(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "target_method": "HEURISTIC",
                "max_turnover_pct": "0.15",
                "enable_tax_awareness": True,
                "max_realized_capital_gains": "100",
                "enable_settlement_awareness": False,
            }
        }
    }

    valuation_mode: ValuationMode = Field(
        default=ValuationMode.CALCULATED,
        description="Valuation source policy.",
        examples=["CALCULATED"],
    )
    target_method: TargetMethod = Field(
        default=TargetMethod.HEURISTIC,
        description="Stage-3 target generation method.",
        examples=["HEURISTIC"],
    )
    compare_target_methods: bool = Field(
        default=False,
        description="Run both target methods and include divergence diagnostics.",
        examples=[False],
    )
    compare_target_methods_tolerance: Decimal = Field(
        default=Decimal("0.0001"),
        description="Tolerance used when comparing method outputs.",
        examples=["0.0001"],
    )

    cash_band_min_weight: Decimal = Field(
        default=Decimal("0.00"),
        description="Lower soft bound for cash weight.",
        examples=["0.00"],
    )
    cash_band_max_weight: Decimal = Field(
        default=Decimal("1.00"),
        description="Upper soft bound for cash weight.",
        examples=["1.00"],
    )

    single_position_max_weight: Optional[Decimal] = Field(
        default=None,
        description="Hard maximum weight allowed for a single position.",
        examples=["0.30"],
    )
    min_trade_notional: Optional[Money] = Field(
        default=None,
        description="Request-level minimum trade notional threshold.",
    )

    allow_restricted: bool = Field(
        default=False,
        description="Allow buys in RESTRICTED shelf instruments.",
        examples=[False],
    )
    suppress_dust_trades: bool = Field(
        default=True,
        description="Suppress trades under minimum notional threshold.",
        examples=[True],
    )
    dust_trade_threshold: Optional[Money] = Field(
        default=None,
        description="Reserved field; currently not consumed by engine logic.",
    )
    fx_buffer_pct: Decimal = Field(
        default=Decimal("0.01"),
        description="Buffer applied when generating FX funding intents.",
        examples=["0.01"],
    )
    block_on_missing_prices: bool = Field(
        default=True,
        description="Block run when required prices are missing.",
        examples=[True],
    )
    block_on_missing_fx: bool = Field(
        default=True,
        description="Block run when required FX rates are missing.",
        examples=[True],
    )
    min_cash_buffer_pct: Decimal = Field(
        default=Decimal("0.0"),
        description="Minimum cash buffer preserved during target generation.",
        examples=["0.05"],
    )
    max_turnover_pct: Optional[Decimal] = Field(
        default=None,
        description="Optional turnover cap as percentage of portfolio value.",
        examples=["0.15"],
    )
    enable_tax_awareness: bool = Field(
        default=False,
        description="Enable tax-aware lot-based sell allocation.",
        examples=[True],
    )
    max_realized_capital_gains: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Optional run-level realized capital gains budget in base currency.",
        examples=["100"],
    )
    enable_settlement_awareness: bool = Field(
        default=False,
        description="Enable settlement-time cash ladder overdraft checks.",
        examples=[True],
    )
    enable_proposal_simulation: bool = Field(
        default=False,
        description="Enable advisory proposal simulation endpoint behavior.",
        examples=[False],
    )
    enable_workflow_gates: bool = Field(
        default=True,
        description="Enable deterministic workflow gate decision output.",
        examples=[True],
    )
    workflow_requires_client_consent: bool = Field(
        default=False,
        description=(
            "Require client consent before execution in gate-decision policy. "
            "Typically true for advisory and false for discretionary mandates."
        ),
        examples=[False],
    )
    client_consent_already_obtained: bool = Field(
        default=False,
        description=(
            "Signals that client consent has already been obtained, allowing "
            "gate progression to execution-ready when policy permits."
        ),
        examples=[False],
    )
    proposal_apply_cash_flows_first: bool = Field(
        default=True,
        description="Apply proposal cash flows before manual trade simulation.",
        examples=[True],
    )
    proposal_block_negative_cash: bool = Field(
        default=True,
        description="Block proposal when cash-flow withdrawals create negative balances.",
        examples=[True],
    )
    link_buy_to_same_currency_sell_dependency: Optional[bool] = Field(
        default=None,
        description=(
            "Attach BUY intent dependency to a same-currency SELL intent. "
            "When null, advisory runtime keeps the default disabled unless explicitly enabled."
        ),
        examples=[None, True, False],
    )
    enable_drift_analytics: bool = Field(
        default=True,
        description="Enable advisory drift analytics when a reference model is provided.",
        examples=[True],
    )
    enable_suitability_scanner: bool = Field(
        default=True,
        description="Enable advisory suitability scanner output in proposal simulation results.",
        examples=[True],
    )
    suitability_thresholds: SuitabilityThresholds = Field(
        default_factory=SuitabilityThresholds,
        description="Threshold settings used by advisory suitability scanner checks.",
    )
    enable_instrument_drift: bool = Field(
        default=True,
        description="Enable instrument-level drift analytics when reference targets are present.",
        examples=[True],
    )
    drift_top_contributors_limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum bucket count in top-contributor and highlight lists.",
        examples=[5],
    )
    drift_unmodeled_exposure_threshold: Decimal = Field(
        default=Decimal("0.01"),
        ge=0,
        le=1,
        description="Minimum exposure threshold for unmodeled-exposure highlights.",
        examples=["0.01"],
    )
    auto_funding: bool = Field(
        default=True,
        description="Enable advisory auto-funding for foreign-currency proposal buys.",
        examples=[True],
    )
    funding_mode: Literal["AUTO_FX"] = Field(
        default="AUTO_FX",
        description="Advisory proposal funding mode.",
        examples=["AUTO_FX"],
    )
    fx_funding_source_currency: Literal["BASE_ONLY", "ANY_CASH"] = Field(
        default="ANY_CASH",
        description="Funding source selection policy for generated advisory FX intents.",
        examples=["ANY_CASH"],
    )
    fx_generation_policy: Literal["ONE_FX_PER_CCY"] = Field(
        default="ONE_FX_PER_CCY",
        description="FX intent generation policy for advisory auto-funding.",
        examples=["ONE_FX_PER_CCY"],
    )
    settlement_horizon_days: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Settlement ladder horizon in day offsets from T+0.",
        examples=[5],
    )
    fx_settlement_days: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Settlement lag used for generated FX intents.",
        examples=[2],
    )
    max_overdraft_by_ccy: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Optional overdraft allowance by currency for settlement ladder.",
        examples=[{"USD": "1000"}],
    )

    # Key format: "<attribute_key>:<attribute_value>", for example "sector:TECH"
    group_constraints: Dict[str, GroupConstraint] = Field(
        default_factory=dict,
        description="Group constraint map keyed by '<attribute_key>:<attribute_value>'.",
        examples=[{"sector:TECH": {"max_weight": "0.25"}}],
    )

    @field_validator("group_constraints")
    @classmethod
    def validate_group_constraint_keys(
        cls, v: Dict[str, GroupConstraint]
    ) -> Dict[str, GroupConstraint]:
        return _validate_group_constraint_keys(v)

    @field_validator("max_turnover_pct")
    @classmethod
    def validate_max_turnover_pct(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        return _validate_optional_ratio_between_zero_and_one(v, field_name="max_turnover_pct")

    @field_validator("max_overdraft_by_ccy")
    @classmethod
    def validate_max_overdraft_by_ccy(cls, v: Dict[str, Decimal]) -> Dict[str, Decimal]:
        return _validate_non_negative_amounts_by_currency(v, field_name="max_overdraft_by_ccy")


__all__ = [
    "EngineOptions",
    "GroupConstraint",
    "SuitabilityThresholds",
    "TargetMethod",
    "ValuationMode",
]
