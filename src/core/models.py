"""
FILE: src/core/models.py
"""

from decimal import Decimal
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.advisory.alternatives_models import ProposalAlternatives, ProposalAlternativesRequest
from src.core.advisory.decision_summary_models import ProposalDecisionSummary
from src.core.advisory.narrative_models import ProposalNarrativeRequest
from src.core.diagnostics_models import (
    CashLadderBreach as CashLadderBreach,
)
from src.core.diagnostics_models import (
    CashLadderPoint as CashLadderPoint,
)
from src.core.diagnostics_models import (
    DiagnosticsData as DiagnosticsData,
)
from src.core.diagnostics_models import (
    DroppedIntent as DroppedIntent,
)
from src.core.diagnostics_models import (
    FundingPlanEntry as FundingPlanEntry,
)
from src.core.diagnostics_models import (
    GroupConstraintEvent as GroupConstraintEvent,
)
from src.core.diagnostics_models import (
    InsufficientCashEntry as InsufficientCashEntry,
)
from src.core.diagnostics_models import (
    LineageData as LineageData,
)
from src.core.diagnostics_models import (
    RuleResult as RuleResult,
)
from src.core.diagnostics_models import (
    SuppressedIntent as SuppressedIntent,
)
from src.core.diagnostics_models import (
    TaxBudgetConstraintEvent as TaxBudgetConstraintEvent,
)
from src.core.drift_models import (
    DriftAnalysis as DriftAnalysis,
)
from src.core.drift_models import (
    DriftBucketDetail as DriftBucketDetail,
)
from src.core.drift_models import (
    DriftDimensionAnalysis as DriftDimensionAnalysis,
)
from src.core.drift_models import (
    DriftHighlightEntry as DriftHighlightEntry,
)
from src.core.drift_models import (
    DriftHighlights as DriftHighlights,
)
from src.core.drift_models import (
    DriftReferenceModelSummary as DriftReferenceModelSummary,
)
from src.core.drift_models import (
    DriftUnmodeledExposure as DriftUnmodeledExposure,
)
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
from src.core.order_intent_models import (
    CashFlowIntent as CashFlowIntent,
)
from src.core.order_intent_models import (
    FxSpotIntent as FxSpotIntent,
)
from src.core.order_intent_models import (
    IntentRationale as IntentRationale,
)
from src.core.order_intent_models import (
    OrderIntent as OrderIntent,
)
from src.core.order_intent_models import (
    ProposalOrderIntent as ProposalOrderIntent,
)
from src.core.order_intent_models import (
    SecurityTradeIntent as SecurityTradeIntent,
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
from src.core.suitability_models import (
    SuitabilityEvidence as SuitabilityEvidence,
)
from src.core.suitability_models import (
    SuitabilityEvidenceSnapshotIds as SuitabilityEvidenceSnapshotIds,
)
from src.core.suitability_models import (
    SuitabilityIssue as SuitabilityIssue,
)
from src.core.suitability_models import (
    SuitabilityResult as SuitabilityResult,
)
from src.core.suitability_models import (
    SuitabilitySummary as SuitabilitySummary,
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
