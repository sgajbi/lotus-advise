"""
FILE: src/core/models.py
"""

from decimal import Decimal
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.advisory.alternatives_models import ProposalAlternatives, ProposalAlternativesRequest
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory.narrative_models import ProposalNarrativeRequest
from src.core.engine_options_models import (
    EngineOptions as EngineOptions,
)
from src.core.engine_options_models import (
    GroupConstraint as GroupConstraint,
)
from src.core.engine_options_models import (
    SuitabilityThresholds as SuitabilityThresholds,
)
from src.core.engine_options_models import (
    TargetMethod as TargetMethod,
)
from src.core.engine_options_models import (
    ValuationMode as ValuationMode,
)
from src.core.portfolio_models import (
    CashBalance as CashBalance,
)
from src.core.portfolio_models import (
    FxRate as FxRate,
)
from src.core.portfolio_models import (
    MarketDataSnapshot as MarketDataSnapshot,
)
from src.core.portfolio_models import (
    ModelPortfolio as ModelPortfolio,
)
from src.core.portfolio_models import (
    ModelTarget as ModelTarget,
)
from src.core.portfolio_models import (
    Money as Money,
)
from src.core.portfolio_models import (
    PortfolioSnapshot as PortfolioSnapshot,
)
from src.core.portfolio_models import (
    Position as Position,
)
from src.core.portfolio_models import (
    Price as Price,
)
from src.core.portfolio_models import (
    ReferenceAssetClassTarget as ReferenceAssetClassTarget,
)
from src.core.portfolio_models import (
    ReferenceInstrumentTarget as ReferenceInstrumentTarget,
)
from src.core.portfolio_models import (
    ReferenceModel as ReferenceModel,
)
from src.core.portfolio_models import (
    ShelfEntry as ShelfEntry,
)
from src.core.portfolio_models import (
    TaxLot as TaxLot,
)
from src.core.simulation_state_models import (
    AllocationMetric as AllocationMetric,
)
from src.core.simulation_state_models import (
    PositionSummary as PositionSummary,
)
from src.core.simulation_state_models import (
    ProposalAllocationBucket as ProposalAllocationBucket,
)
from src.core.simulation_state_models import (
    ProposalAllocationDimension as ProposalAllocationDimension,
)
from src.core.simulation_state_models import (
    ProposalAllocationLens as ProposalAllocationLens,
)
from src.core.simulation_state_models import (
    ProposalAllocationView as ProposalAllocationView,
)
from src.core.simulation_state_models import (
    SimulatedState as SimulatedState,
)
from src.core.universe_target_models import (
    ExcludedInstrument as ExcludedInstrument,
)
from src.core.universe_target_models import (
    TargetData as TargetData,
)
from src.core.universe_target_models import (
    TargetInstrument as TargetInstrument,
)
from src.core.universe_target_models import (
    UniverseCoverage as UniverseCoverage,
)
from src.core.universe_target_models import (
    UniverseData as UniverseData,
)


def _is_python_float(candidate: object) -> bool:
    type_name = candidate.__class__.__name__
    if type_name == "float":
        return True
    return False


class IntentRationale(BaseModel):
    code: str = Field(description="Short rationale code for generated intent.")
    message: str = Field(description="Human-readable rationale message.")


class SecurityTradeIntent(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = Field(
        default="SECURITY_TRADE",
        description="Intent discriminator.",
    )
    intent_id: str = Field(description="Intent identifier unique within run.")
    instrument_id: str = Field(description="Instrument identifier for trade.")
    side: Literal["BUY", "SELL"] = Field(description="Trade side.")
    quantity: Optional[Decimal] = Field(default=None, description="Trade quantity.")
    notional: Optional[Money] = Field(
        default=None, description="Trade notional in instrument currency."
    )
    notional_base: Optional[Money] = Field(
        default=None, description="Trade notional converted to base currency."
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this intent."
    )
    constraints_applied: List[str] = Field(
        default_factory=list,
        description="Constraint labels applied during sizing.",
    )


class FxSpotIntent(BaseModel):
    intent_type: Literal["FX_SPOT"] = Field(default="FX_SPOT", description="Intent discriminator.")
    intent_id: str = Field(description="Intent identifier unique within run.")
    pair: str = Field(description="FX pair of the conversion intent.")
    buy_currency: str = Field(description="Currency bought by this FX trade.")
    buy_amount: Decimal = Field(description="Estimated amount bought.")
    sell_currency: str = Field(description="Currency sold by this FX trade.")
    sell_amount_estimated: Decimal = Field(description="Estimated amount sold.")
    dependencies: List[str] = Field(
        default_factory=list, description="Intent ids that must execute first."
    )
    rationale: Optional[IntentRationale] = Field(
        default=None, description="Rationale for this FX intent."
    )


class CashFlowIntent(BaseModel):
    intent_type: Literal["CASH_FLOW"] = Field(
        default="CASH_FLOW",
        description="Intent discriminator.",
        examples=["CASH_FLOW"],
    )
    intent_id: str = Field(description="Intent identifier unique within run.", examples=["oi_cf_1"])
    currency: str = Field(description="Cash-flow currency code.", examples=["USD"])
    amount: Decimal = Field(description="Signed cash-flow amount.", examples=["2000.00"])
    description: Optional[str] = Field(
        default=None,
        description="Optional advisor-entered note.",
        examples=["Client top-up"],
    )


OrderIntent = Union[SecurityTradeIntent, FxSpotIntent]
ProposalOrderIntent = Union[CashFlowIntent, FxSpotIntent, SecurityTradeIntent]


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


class Reconciliation(BaseModel):
    before_total_value: Money = Field(description="Before-state total value.")
    after_total_value: Money = Field(description="After-state total value.")
    delta: Money = Field(description="After minus before.")
    tolerance: Money = Field(description="Allowed reconciliation tolerance.")
    status: Literal["OK", "MISMATCH"] = Field(description="Reconciliation outcome.")


class TaxImpact(BaseModel):
    total_realized_gain: Money = Field(
        description="Aggregate realized gain from constrained sell allocation."
    )
    total_realized_loss: Money = Field(
        description="Aggregate realized loss from constrained sell allocation."
    )
    budget_limit: Optional[Money] = Field(default=None, description="Configured gains budget.")
    budget_used: Optional[Money] = Field(default=None, description="Portion of budget consumed.")


class DriftReferenceModelSummary(BaseModel):
    model_id: str = Field(description="Reference model identifier.")
    as_of: str = Field(description="Reference model as-of date.")
    base_currency: str = Field(description="Reference model base currency.")


class DriftBucketDetail(BaseModel):
    bucket: str = Field(description="Drift bucket key.")
    model_weight: Decimal = Field(description="Reference model weight for the bucket.")
    portfolio_weight_before: Decimal = Field(
        description="Before-state portfolio weight for the bucket."
    )
    portfolio_weight_after: Decimal = Field(
        description="After-state portfolio weight for the bucket."
    )
    drift_before: Decimal = Field(description="Signed before-state drift for the bucket.")
    drift_after: Decimal = Field(description="Signed after-state drift for the bucket.")
    abs_drift_before: Decimal = Field(description="Absolute before-state drift for the bucket.")
    abs_drift_after: Decimal = Field(description="Absolute after-state drift for the bucket.")
    improvement: Decimal = Field(description="Positive when absolute drift improves.")


class DriftDimensionAnalysis(BaseModel):
    drift_total_before: Decimal = Field(description="Total drift in before-state.")
    drift_total_after: Decimal = Field(description="Total drift in after-state.")
    drift_total_delta: Decimal = Field(
        description="After minus before drift total. Negative means improvement."
    )
    top_contributors_before: List[DriftBucketDetail] = Field(
        default_factory=list,
        description="Largest before-state drift contributors.",
    )
    buckets: List[DriftBucketDetail] = Field(
        default_factory=list,
        description="Deterministic drift details for all buckets.",
    )


class DriftHighlightEntry(BaseModel):
    bucket: str = Field(description="Highlighted drift bucket.")
    improvement: Decimal = Field(description="Improvement value for the highlighted bucket.")


class DriftUnmodeledExposure(BaseModel):
    bucket: str = Field(description="Bucket with model weight of zero.")
    portfolio_weight_before: Decimal = Field(description="Before-state exposure for the bucket.")
    portfolio_weight_after: Decimal = Field(description="After-state exposure for the bucket.")
    max_portfolio_weight: Decimal = Field(
        description="Max of before/after exposure for the bucket."
    )


class DriftHighlights(BaseModel):
    largest_improvements: List[DriftHighlightEntry] = Field(
        default_factory=list,
        description="Buckets with largest positive drift improvements.",
    )
    largest_deteriorations: List[DriftHighlightEntry] = Field(
        default_factory=list,
        description="Buckets with largest drift deteriorations.",
    )
    unmodeled_exposures: List[DriftUnmodeledExposure] = Field(
        default_factory=list,
        description="Buckets where model weight is zero and exposure exceeds threshold.",
    )


class DriftAnalysis(BaseModel):
    reference_model: DriftReferenceModelSummary = Field(
        description="Reference model identifier details."
    )
    asset_class: DriftDimensionAnalysis = Field(description="Asset-class drift analytics.")
    instrument: Optional[DriftDimensionAnalysis] = Field(
        default=None,
        description="Instrument drift analytics when instrument targets are provided.",
    )
    highlights: DriftHighlights = Field(description="Deterministic advisory highlights.")


class SuitabilityEvidenceSnapshotIds(BaseModel):
    portfolio_snapshot_id: str = Field(
        description="Portfolio snapshot id used as evidence source.",
        examples=["PB_SG_GLOBAL_BAL_001"],
    )
    market_data_snapshot_id: str = Field(
        description="Market-data snapshot id used as evidence source.",
        examples=["md_2026_02_19"],
    )


class SuitabilityEvidence(BaseModel):
    as_of: str = Field(
        description="Suitability evidence as-of identifier derived from request snapshots.",
        examples=["md_2026_02_19"],
    )
    snapshot_ids: SuitabilityEvidenceSnapshotIds = Field(
        description="Snapshot identifiers used by suitability checks."
    )


class SuitabilityIssue(BaseModel):
    issue_id: str = Field(
        description="Stable suitability issue identifier.",
        examples=["SUIT_SINGLE_POSITION_MAX"],
    )
    issue_key: str = Field(
        description="Deterministic issue key used for before/after classification.",
        examples=["SINGLE_POSITION_MAX|US_EQ_ETF"],
    )
    dimension: Literal[
        "CONCENTRATION",
        "ISSUER",
        "LIQUIDITY",
        "GOVERNANCE",
        "PRODUCT",
        "CASH",
        "DATA_QUALITY",
    ] = Field(
        description="Suitability issue dimension.",
        examples=["CONCENTRATION"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Advisory suitability severity level.",
        examples=["HIGH"],
    )
    status_change: Literal["NEW", "RESOLVED", "PERSISTENT"] = Field(
        description="Before/after suitability state transition class.",
        examples=["NEW"],
    )
    classification: Literal[
        "NEW",
        "RESOLVED",
        "PERSISTENT",
        "UNKNOWN_DUE_TO_MISSING_EVIDENCE",
    ] = Field(
        description="Enterprise suitability classification used by decision policy.",
        examples=["UNKNOWN_DUE_TO_MISSING_EVIDENCE"],
    )
    summary: str = Field(
        description="Short suitability issue narrative.",
        examples=["Single position exceeds 10% cap."],
    )
    remediation: Optional[str] = Field(
        default=None,
        description="Deterministic advisor remediation guidance for the issue.",
        examples=["Capture client knowledge and experience evidence before proceeding."],
    )
    approval_implication: Optional[str] = Field(
        default=None,
        description="Approval or review implication triggered by this issue.",
        examples=["COMPLIANCE_REVIEW"],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic suitability measurement details encoded as strings.",
        examples=[
            {
                "threshold": "0.10",
                "measured_before": "0.12",
                "measured_after": "0.09",
                "instrument_id": "US_EQ_ETF",
            }
        ],
    )
    evidence: SuitabilityEvidence = Field(description="Evidence lineage for this issue.")
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Suitability policy-pack identifier that produced the issue.",
        examples=["global-private-banking-baseline"],
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Suitability policy version that produced the issue.",
        examples=["enterprise-suitability-policy.2026-04"],
    )


class SuitabilitySummary(BaseModel):
    new_count: int = Field(description="Count of NEW suitability issues.", examples=[1])
    resolved_count: int = Field(description="Count of RESOLVED suitability issues.", examples=[2])
    persistent_count: int = Field(
        description="Count of PERSISTENT suitability issues.",
        examples=[3],
    )
    highest_severity_new: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = Field(
        default=None,
        description="Highest severity among NEW issues, when present.",
        examples=["HIGH"],
    )


class SuitabilityResult(BaseModel):
    summary: SuitabilitySummary = Field(description="Suitability issue summary counts.")
    issues: List[SuitabilityIssue] = Field(
        default_factory=list,
        description="Deterministic ordered suitability issue list.",
    )
    policy_pack_id: Optional[str] = Field(
        default=None,
        description="Suitability policy-pack identifier used for this evaluation.",
        examples=["global-private-banking-baseline"],
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Suitability policy version used for this evaluation.",
        examples=["enterprise-suitability-policy.2026-04"],
    )
    recommended_gate: Literal["NONE", "RISK_REVIEW", "COMPLIANCE_REVIEW"] = Field(
        description="Advisory gate recommendation derived from NEW issue severities.",
        examples=["COMPLIANCE_REVIEW"],
    )


class GateReason(BaseModel):
    reason_code: str = Field(
        description="Stable workflow reason code.",
        examples=["HARD_RULE_FAIL:INSUFFICIENT_CASH"],
    )
    severity: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        description="Reason severity level used for deterministic ordering.",
        examples=["HIGH"],
    )
    source: Literal["RULE_ENGINE", "SUITABILITY", "DATA_QUALITY"] = Field(
        description="Reason source subsystem.",
        examples=["RULE_ENGINE"],
    )
    details: Dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic structured details for the reason.",
    )


class GateDecisionSummary(BaseModel):
    hard_fail_count: int = Field(description="Count of hard rule failures.", examples=[1])
    soft_fail_count: int = Field(description="Count of soft rule failures.", examples=[0])
    new_high_suitability_count: int = Field(
        description="Count of NEW suitability issues with HIGH severity.",
        examples=[0],
    )
    new_medium_suitability_count: int = Field(
        description="Count of NEW suitability issues with MEDIUM severity.",
        examples=[0],
    )


class GateDecision(BaseModel):
    gate: Literal[
        "BLOCKED",
        "RISK_REVIEW_REQUIRED",
        "COMPLIANCE_REVIEW_REQUIRED",
        "CLIENT_CONSENT_REQUIRED",
        "EXECUTION_READY",
        "NONE",
    ] = Field(
        description="Deterministic workflow gate outcome.",
        examples=["CLIENT_CONSENT_REQUIRED"],
    )
    recommended_next_step: Literal[
        "FIX_INPUT",
        "RISK_REVIEW",
        "COMPLIANCE_REVIEW",
        "REQUEST_CLIENT_CONSENT",
        "EXECUTE",
        "NONE",
    ] = Field(
        description="Recommended next workflow step based on gate policy.",
        examples=["REQUEST_CLIENT_CONSENT"],
    )
    reasons: List[GateReason] = Field(
        default_factory=list,
        description="Deterministic ordered reasons explaining the gate.",
    )
    summary: GateDecisionSummary = Field(description="Gate summary counters.")


class ProposedCashFlow(BaseModel):
    intent_type: Literal["CASH_FLOW"] = Field(
        default="CASH_FLOW",
        description="Intent discriminator for advisory cash-flow proposals.",
        examples=["CASH_FLOW"],
    )
    currency: str = Field(description="Cash-flow currency code.", examples=["USD"])
    amount: Decimal = Field(
        description="Signed cash-flow amount as decimal string.",
        examples=["2000.00", "-500.00"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional advisor-entered narrative for this cash flow.",
        examples=["Client deposit before switch"],
    )

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float_amount(cls, v: object) -> object:
        if _is_python_float(v):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: amount must be a decimal string")
        return v


class ProposedTrade(BaseModel):
    intent_type: Literal["SECURITY_TRADE"] = Field(
        default="SECURITY_TRADE",
        description="Intent discriminator for advisory security trades.",
        examples=["SECURITY_TRADE"],
    )
    side: Literal["BUY", "SELL"] = Field(description="Manual trade side.", examples=["BUY"])
    instrument_id: str = Field(
        description="Instrument identifier for manual trade.",
        examples=["EQ_GROWTH"],
    )
    quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Trade quantity. Required when `notional` is not provided.",
        examples=["40"],
    )
    notional: Optional[Money] = Field(
        default=None,
        description=(
            "Trade notional in instrument currency. Required when `quantity` is not provided."
        ),
        examples=[{"amount": "2000.00", "currency": "USD"}],
    )

    @field_validator("quantity", mode="before")
    @classmethod
    def reject_float_quantity(cls, v: object) -> object:
        if _is_python_float(v):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: quantity must be a decimal string")
        return v

    @field_validator("notional", mode="before")
    @classmethod
    def reject_float_notional_amount(cls, v: object) -> object:
        if isinstance(v, dict) and _is_python_float(v.get("amount")):
            raise ValueError(
                "PROPOSAL_INVALID_TRADE_INPUT: notional.amount must be a decimal string"
            )
        return v

    @model_validator(mode="after")
    def validate_quantity_or_notional(self) -> "ProposedTrade":
        if self.quantity is None and self.notional is None:
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: quantity or notional is required")
        if self.quantity is not None and self.notional is not None:
            raise ValueError(
                "PROPOSAL_INVALID_TRADE_INPUT: provide either quantity or notional, not both"
            )
        if self.notional is not None and self.notional.amount <= Decimal("0"):
            raise ValueError("PROPOSAL_INVALID_TRADE_INPUT: notional.amount must be greater than 0")
        return self


class ProposalSimulateRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "portfolio_snapshot": {
                    "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                    "base_currency": "USD",
                    "positions": [{"instrument_id": "EQ_LEGACY", "quantity": "100"}],
                    "cash_balances": [{"currency": "USD", "amount": "5000.00"}],
                },
                "market_data_snapshot": {
                    "prices": [
                        {"instrument_id": "EQ_LEGACY", "price": "100.00", "currency": "USD"},
                        {"instrument_id": "EQ_GROWTH", "price": "50.00", "currency": "USD"},
                    ],
                    "fx_rates": [],
                },
                "shelf_entries": [
                    {"instrument_id": "EQ_LEGACY", "status": "APPROVED"},
                    {"instrument_id": "EQ_GROWTH", "status": "APPROVED"},
                ],
                "options": {
                    "enable_proposal_simulation": True,
                    "proposal_apply_cash_flows_first": True,
                    "proposal_block_negative_cash": True,
                    "block_on_missing_prices": True,
                    "block_on_missing_fx": True,
                },
                "proposed_cash_flows": [
                    {
                        "intent_type": "CASH_FLOW",
                        "currency": "USD",
                        "amount": "2000.00",
                        "description": "Client top-up",
                    }
                ],
                "proposed_trades": [
                    {
                        "intent_type": "SECURITY_TRADE",
                        "side": "BUY",
                        "instrument_id": "EQ_GROWTH",
                        "quantity": "40",
                    }
                ],
            }
        }
    }

    portfolio_snapshot: PortfolioSnapshot = Field(
        description="Current portfolio holdings and cash balances.",
        examples=[
            {
                "portfolio_id": "PB_SG_GLOBAL_BAL_001",
                "base_currency": "USD",
                "positions": [{"instrument_id": "EQ_LEGACY", "quantity": "100"}],
                "cash_balances": [{"currency": "USD", "amount": "5000.00"}],
            }
        ],
    )
    market_data_snapshot: MarketDataSnapshot = Field(
        description="Price and FX snapshot used for proposal simulation.",
        examples=[
            {
                "prices": [
                    {"instrument_id": "EQ_LEGACY", "price": "100.00", "currency": "USD"},
                    {"instrument_id": "EQ_GROWTH", "price": "50.00", "currency": "USD"},
                ],
                "fx_rates": [],
            }
        ],
    )
    shelf_entries: List[ShelfEntry] = Field(
        description="Instrument eligibility and policy metadata.",
        examples=[
            [
                {"instrument_id": "EQ_LEGACY", "status": "APPROVED"},
                {"instrument_id": "EQ_GROWTH", "status": "APPROVED"},
            ]
        ],
    )
    options: EngineOptions = Field(
        default_factory=EngineOptions,
        description="Request-level engine behavior and feature toggles.",
        examples=[
            {
                "enable_proposal_simulation": True,
                "proposal_apply_cash_flows_first": True,
                "proposal_block_negative_cash": True,
            }
        ],
    )
    proposed_cash_flows: List[ProposedCashFlow] = Field(
        default_factory=list,
        description="Advisor-entered cash flow instructions.",
        examples=[[{"intent_type": "CASH_FLOW", "currency": "USD", "amount": "2000.00"}]],
    )
    proposed_trades: List[ProposedTrade] = Field(
        default_factory=list,
        description="Advisor-entered manual security trade instructions.",
        examples=[
            [
                {
                    "intent_type": "SECURITY_TRADE",
                    "side": "BUY",
                    "instrument_id": "EQ_GROWTH",
                    "quantity": "40",
                }
            ]
        ],
    )
    reference_model: Optional[ReferenceModel] = Field(
        default=None,
        description="Optional reference model used for advisory drift analytics.",
    )
    alternatives_request: ProposalAlternativesRequest | None = Field(
        default=None,
        description=(
            "Optional backend-owned alternatives request for proposal comparison generation."
        ),
    )
    narrative_request: ProposalNarrativeRequest | None = Field(
        default=None,
        description=(
            "Optional advisor-review proposal narrative request. Supports deterministic template "
            "mode and Slice 7 opt-in `AI_ASSISTED_DRAFT`; client-ready commentary remains gated."
        ),
    )


class ProposalResult(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "proposal_run_id": "pr_abc12345",
                "correlation_id": "corr_123abc",
                "status": "READY",
                "intents": [],
                "diagnostics": {
                    "warnings": [],
                    "data_quality": {"price_missing": [], "fx_missing": []},
                },
                "lineage": {"request_hash": "sha256:...", "idempotency_key": "idem-1"},
            }
        }
    }

    proposal_run_id: str = Field(description="Proposal run identifier.", examples=["pr_abc12345"])
    correlation_id: str = Field(
        description="Correlation id used by request logging context.",
        examples=["corr_123abc"],
    )
    status: Literal["READY", "BLOCKED", "PENDING_REVIEW"] = Field(
        description="Top-level domain outcome.",
        examples=["READY"],
    )
    before: SimulatedState = Field(description="Before-state valuation snapshot.")
    intents: List[Annotated[ProposalOrderIntent, Field(discriminator="intent_type")]] = Field(
        description="Deterministically ordered proposal intents applied during simulation.",
        examples=[
            [
                {
                    "intent_type": "CASH_FLOW",
                    "intent_id": "oi_cf_1",
                    "currency": "USD",
                    "amount": "2000.00",
                },
                {
                    "intent_type": "SECURITY_TRADE",
                    "intent_id": "oi_1",
                    "side": "BUY",
                    "instrument_id": "EQ_GROWTH",
                    "quantity": "40",
                },
            ]
        ],
    )
    after_simulated: SimulatedState = Field(description="After-state simulation snapshot.")
    reconciliation: Optional[Reconciliation] = Field(
        default=None, description="Reconciliation output."
    )
    rule_results: List[RuleResult] = Field(
        default_factory=list, description="Rule engine evaluations."
    )
    explanation: Dict[str, Any] = Field(description="Additional explanatory payload.")
    diagnostics: DiagnosticsData = Field(description="Diagnostics and warnings for the run.")
    drift_analysis: Optional[DriftAnalysis] = Field(
        default=None,
        description="Reference-model drift analytics when provided and enabled.",
    )
    suitability: Optional[SuitabilityResult] = Field(
        default=None,
        description="Advisory suitability scanner output with NEW/RESOLVED/PERSISTENT issues.",
    )
    gate_decision: Optional[GateDecision] = Field(
        default=None,
        description="Deterministic workflow gate decision for advisory workflow routing.",
    )
    proposal_decision_summary: Optional[ProposalDecisionSummary] = Field(
        default=None,
        description=(
            "Backend-owned advisory decision summary for UI, artifact, and replay consumers."
        ),
    )
    proposal_alternatives: ProposalAlternatives | None = Field(
        default=None,
        description="Backend-owned proposal alternatives envelope when alternatives are requested.",
    )
    allocation_lens: ProposalAllocationLens = Field(
        default_factory=ProposalAllocationLens,
        description="Canonical allocation-lens metadata for proposal before/after states.",
    )
    lineage: LineageData = Field(description="Lineage identifiers and request hash.")
