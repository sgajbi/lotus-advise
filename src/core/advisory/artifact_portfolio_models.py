from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from src.core.portfolio_models import Money


class ProposalArtifactPortfolioState(BaseModel):
    total_value: Money = Field(description="Total portfolio value in base currency.")
    allocation_by_asset_class: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministically ordered asset-class allocation rows.",
        examples=[
            [
                {
                    "key": "EQUITY",
                    "weight": "0.6200",
                    "value": {"amount": "620000.00", "currency": "USD"},
                }
            ]
        ],
    )
    allocation_by_instrument: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministically ordered instrument allocation rows.",
        examples=[
            [
                {
                    "key": "US_EQ_ETF",
                    "weight": "0.1800",
                    "value": {"amount": "180000.00", "currency": "USD"},
                }
            ]
        ],
    )


class ProposalArtifactWeightChange(BaseModel):
    bucket_type: Literal["INSTRUMENT"] = Field(
        description="Bucket type used for weight-change entries.",
        examples=["INSTRUMENT"],
    )
    bucket_id: str = Field(
        description="Instrument id for the weight-change row.", examples=["EQ_1"]
    )
    weight_before: str = Field(
        description="Before-state weight as a quantized string.",
        examples=["0.1200"],
    )
    weight_after: str = Field(
        description="After-state weight as a quantized string.",
        examples=["0.1800"],
    )
    delta: str = Field(
        description="After-minus-before weight delta as a quantized string.",
        examples=["0.0600"],
    )


class ProposalArtifactPortfolioDelta(BaseModel):
    total_value_delta: Money = Field(description="After minus before total value.")
    largest_weight_changes: List[ProposalArtifactWeightChange] = Field(
        default_factory=list,
        description="Top absolute instrument weight changes in deterministic order.",
    )


class ProposalArtifactPortfolioImpact(BaseModel):
    before: ProposalArtifactPortfolioState = Field(description="Before-state allocation snapshot.")
    after: ProposalArtifactPortfolioState = Field(description="After-state allocation snapshot.")
    delta: ProposalArtifactPortfolioDelta = Field(description="Computed portfolio deltas.")
    reconciliation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Reconciliation payload copied from proposal simulation output.",
    )
