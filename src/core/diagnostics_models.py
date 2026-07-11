from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money
from src.core.source_provenance_models import SourceProvenanceEnvelope


class RuleResult(BaseModel):
    rule_id: str = Field(description="Rule identifier.")
    severity: Literal["HARD", "SOFT", "INFO"] = Field(description="Rule severity tier.")
    status: Literal["PASS", "FAIL"] = Field(description="Rule evaluation outcome.")
    measured: Decimal = Field(description="Measured value used in evaluation.")
    threshold: Dict[str, Decimal] = Field(description="Threshold values applied by the rule.")
    reason_code: str = Field(description="Reason code for rule outcome.")
    remediation_hint: Optional[str] = Field(
        default=None, description="Optional guidance on remediation."
    )


class SuppressedIntent(BaseModel):
    instrument_id: str = Field(description="Instrument id for suppressed trade.")
    reason: str = Field(description="Suppression reason.")
    intended_notional: Money = Field(description="Original intended notional.")
    threshold: Money = Field(description="Suppression threshold that was not met.")


class DroppedIntent(BaseModel):
    instrument_id: str = Field(description="Instrument id for dropped trade under turnover cap.")
    reason: str = Field(description="Drop reason code.")
    potential_notional: Money = Field(description="Potential notional if the trade had been kept.")
    score: Decimal = Field(description="Ranking score used in turnover selection.")


class GroupConstraintEvent(BaseModel):
    constraint_key: str = Field(description="Applied group constraint key.")
    group_weight_before: Decimal = Field(description="Group weight before capping.")
    max_weight: Decimal = Field(description="Configured maximum allowed group weight.")
    released_weight: Decimal = Field(description="Weight released by cap operation.")
    recipients: Dict[str, Decimal] = Field(
        default_factory=dict,
        description="Redistribution recipients and allocated weight shares.",
    )
    status: Literal["CAPPED", "BLOCKED"] = Field(description="Constraint application outcome.")


class TaxBudgetConstraintEvent(BaseModel):
    instrument_id: str = Field(description="Instrument constrained by tax budget.")
    requested_quantity: Decimal = Field(description="Requested sell quantity before budget limit.")
    allowed_quantity: Decimal = Field(description="Allowed sell quantity after budget constraint.")
    reason_code: str = Field(description="Constraint reason code.")


class CashLadderPoint(BaseModel):
    date_offset: int = Field(description="Day offset from T+0.")
    currency: str = Field(description="Currency for projected balance.")
    projected_balance: Decimal = Field(description="Projected cumulative balance on the day.")


class CashLadderBreach(BaseModel):
    date_offset: int = Field(description="Day offset where breach occurs.")
    currency: str = Field(description="Currency where breach occurs.")
    projected_balance: Decimal = Field(description="Projected balance at breach point.")
    allowed_floor: Decimal = Field(description="Configured allowed floor for that currency/day.")
    reason_code: str = Field(description="Breach reason code.")


class FundingPlanEntry(BaseModel):
    target_currency: str = Field(description="Currency required by advisory BUY intents.")
    required: Decimal = Field(description="Total required amount in target currency.")
    available_before_fx: Decimal = Field(
        description="Available amount in target currency before generated FX."
    )
    fx_needed: Decimal = Field(description="Generated FX buy amount needed in target currency.")
    fx_pair: Optional[str] = Field(
        default=None,
        description="Resolved FX pair used for funding, when available.",
    )
    funding_currency: Optional[str] = Field(
        default=None,
        description="Currency sold to fund target-currency buys.",
    )


class InsufficientCashEntry(BaseModel):
    currency: str = Field(description="Currency where funding cash deficit is detected.")
    deficit: Decimal = Field(description="Deficit amount in the funding currency.")


class DiagnosticsData(BaseModel):
    warnings: List[str] = Field(default_factory=list, description="Run-level warning codes.")
    suppressed_intents: List[SuppressedIntent] = Field(
        default_factory=list,
        description="Intents suppressed during generation (for example dust suppression).",
    )
    dropped_intents: List[DroppedIntent] = Field(
        default_factory=list,
        description="Intents dropped by turnover control.",
    )
    group_constraint_events: List[GroupConstraintEvent] = Field(
        default_factory=list,
        description="Group constraint capping/redistribution events.",
    )
    tax_budget_constraint_events: List[TaxBudgetConstraintEvent] = Field(
        default_factory=list,
        description="Tax budget constraint events by instrument.",
    )
    cash_ladder: List[CashLadderPoint] = Field(
        default_factory=list,
        description="Settlement-aware projected cash ladder points.",
    )
    cash_ladder_breaches: List[CashLadderBreach] = Field(
        default_factory=list,
        description="Settlement ladder breaches that trigger blocks.",
    )
    missing_fx_pairs: List[str] = Field(
        default_factory=list,
        description="Missing FX pairs required for generated funding or proposal valuation.",
    )
    funding_plan: List[FundingPlanEntry] = Field(
        default_factory=list,
        description="Advisory funding plan details for generated FX intents.",
    )
    insufficient_cash: List[InsufficientCashEntry] = Field(
        default_factory=list,
        description="Funding deficits that block proposal simulation.",
    )
    data_quality: Dict[str, List[str]] = Field(
        description="Data-quality issue buckets and affected keys."
    )


class LineageData(BaseModel):
    portfolio_snapshot_id: str = Field(description="Portfolio snapshot id used by run.")
    market_data_snapshot_id: str = Field(description="Market-data snapshot id used by run.")
    request_hash: str = Field(description="Request hash/idempotency marker used in lineage.")
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Request idempotency key.",
        examples=["proposal-idem-001"],
    )
    engine_version: Optional[str] = Field(
        default=None,
        description="Engine version identifier.",
        examples=["0.1.0"],
    )
    simulation_contract_version: Optional[str] = Field(
        default=None,
        description="Canonical simulation contract version used for this result.",
        examples=["advisory-simulation.v1"],
    )
    source_provenance: Optional[SourceProvenanceEnvelope] = Field(
        default=None,
        description="Upstream source snapshot, version, freshness, and contract evidence.",
    )


__all__ = [
    "CashLadderBreach",
    "CashLadderPoint",
    "DiagnosticsData",
    "DroppedIntent",
    "FundingPlanEntry",
    "GroupConstraintEvent",
    "InsufficientCashEntry",
    "LineageData",
    "RuleResult",
    "SuppressedIntent",
    "TaxBudgetConstraintEvent",
]
